from datetime import datetime
from uuid import UUID
import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundException, ValidationException
from app.core.storage.azure_blob import get_azure_blob_service
from app.modules.ai_processing.models import AIModel, AIProcessingJob, AIProcessingStatus, AIConfidenceThreshold, AIReviewTask, AIModelType, AIModelProvider
from app.modules.ai_processing.repository import AIModelRepository, AIProcessingJobRepository, AIConfidenceThresholdRepository, AIReviewTaskRepository
from app.modules.ai_processing.schemas import (
    AIModelCreate,
    AIModelUpdate,
    AIProcessingJobCreate,
    AIProcessingJobUpdate,
    AIProcessRequest,
    AIConfidenceThresholdCreate,
    AIConfidenceThresholdUpdate,
    AIReviewTaskCreate,
    AIReviewTaskUpdate,
)
from app.modules.documents.models import Document
from app.modules.users.models import User


class AIModelService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AIModelRepository(db)

    async def create(self, data: dict, tenant_id: UUID, created_by: UUID) -> AIModel:
        model = AIModel(
            **data,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return model

    async def get_by_id(self, model_id: UUID, tenant_id: UUID) -> AIModel:
        model = await self.repository.get_by_id(model_id, tenant_id)
        if not model:
            raise NotFoundException(detail="AI model not found")
        return model

    async def get_default(self, model_type: str, tenant_id: UUID) -> AIModel:
        model = await self.repository.get_default(model_type, tenant_id)
        if not model:
            raise NotFoundException(detail=f"No default model found for type {model_type}")
        return model

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        model_type: str | None = None,
        provider: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list, int]:
        return await self.repository.get_all(tenant_id, page, page_size, model_type, provider, is_active)

    async def update(self, model_id: UUID, tenant_id: UUID, data: dict, updated_by: UUID) -> AIModel:
        model = await self.get_by_id(model_id, tenant_id)

        for field, value in data.items():
            if hasattr(model, field):
                setattr(model, field, value)

        model.updated_at = datetime.now()
        await self.db.flush()
        await self.db.refresh(model)
        return model

    async def delete(self, model_id: UUID, tenant_id: UUID) -> None:
        model = await self.get_by_id(model_id, tenant_id)
        await self.db.delete(model)
        await self.db.flush()

    async def set_default(self, model_id: UUID, tenant_id: UUID) -> AIModel:
        model = await self.get_by_id(model_id, tenant_id)

        result = await self.db.execute(
            select(AIModel).where(
                AIModel.model_type == model.model_type,
                AIModel.tenant_id == tenant_id,
                AIModel.is_default == True,
            )
        )
        current_default = result.scalars().first()
        if current_default:
            current_default.is_default = False

        model.is_default = True
        await self.db.flush()
        await self.db.refresh(model)
        return model


class AIProcessingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_repository = AIProcessingJobRepository(db)
        self.model_repository = AIModelRepository(db)
        self.settings = get_settings()

    async def _download_document(self, document: Document) -> bytes:
        azure_service = get_azure_blob_service()
        return await azure_service.download_blob(document.storage_key)

    async def _get_document_text(self, document: Document) -> str:
        if document.ocr_text:
            return document.ocr_text

        file_content = await self._download_document(document)

        if document.mime_type and document.mime_type.startswith("text/"):
            return file_content.decode("utf-8", errors="replace")

        return f"[Document: {document.filename}, size: {len(file_content)} bytes]"

    def _build_prompt(self, model: AIModel, request: dict, document_text: str) -> str:
        base_prompt = request.get("prompt", "")
        input_data = request.get("input_data", {})

        if model.model_type == AIModelType.CLASSIFICATION:
            prompt = f"""Classify the following document into one of the predefined categories.
Document text:
{document_text[:8000]}

Return a JSON object with:
- category: the classification category
- confidence: confidence score (0-1)
- reasoning: brief explanation"""

        elif model.model_type == AIModelType.EXTRACTION:
            fields = input_data.get("fields", [])
            fields_str = ", ".join(fields) if fields else "all relevant fields"
            prompt = f"""Extract the following fields from the document:
Fields to extract: {fields_str}

Document text:
{document_text[:8000]}

Return a JSON object with extracted field names as keys and their values. Include confidence scores for each field."""

        elif model.model_type == AIModelType.SUMMARIZATION:
            prompt = f"""Summarize the following document:
{document_text[:8000]}

Return a JSON object with:
- summary: concise summary
- key_points: list of key points
- confidence: confidence score (0-1)"""

        elif model.model_type == AIModelType.ENTITY_RECOGNITION:
            prompt = f"""Extract named entities from the following document:
{document_text[:8000]}

Return a JSON object with entities categorized by type (person, organization, location, date, etc.)"""

        else:
            prompt = base_prompt or f"Process the following document:\n{document_text[:8000]}"

        return prompt

    async def _call_openai(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import openai

        api_key = model.credentials.get("api_key")
        if not api_key:
            raise ValidationException("OpenAI API key not configured")

        client = openai.AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model=model.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=model.config.get("temperature", 0.1),
            max_tokens=model.config.get("max_tokens", 2000),
            response_format={"type": "json_object"} if model.config.get("json_mode", True) else None,
        )

        output_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        try:
            output_data = json.loads(output_text)
        except json.JSONDecodeError:
            output_data = {"raw_output": output_text}

        cost = (tokens_used / 1000) * 0.01

        return output_data, tokens_used, cost

    async def _call_anthropic(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import anthropic

        api_key = model.credentials.get("api_key")
        if not api_key:
            raise ValidationException("Anthropic API key not configured")

        client = anthropic.AsyncAnthropic(api_key=api_key)

        response = await client.messages.create(
            model=model.model_name,
            max_tokens=model.config.get("max_tokens", 2000),
            temperature=model.config.get("temperature", 0.1),
            messages=[{"role": "user", "content": prompt}],
        )

        output_text = response.content[0].text if response.content else ""
        tokens_used = response.usage.input_tokens + response.usage.output_tokens if response.usage else 0

        try:
            output_data = json.loads(output_text)
        except json.JSONDecodeError:
            output_data = {"raw_output": output_text}

        cost = (tokens_used / 1000) * 0.015

        return output_data, tokens_used, cost

    async def _call_google(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import google.generativeai as genai

        api_key = model.credentials.get("api_key")
        if not api_key:
            raise ValidationException("Google API key not configured")

        genai.configure(api_key=api_key)
        gm = genai.GenerativeModel(model.model_name)

        response = await gm.generate_content_async(prompt)
        output_text = response.text if response.text else ""
        tokens_used = 0

        try:
            output_data = json.loads(output_text)
        except json.JSONDecodeError:
            output_data = {"raw_output": output_text}

        cost = 0.0

        return output_data, tokens_used, cost

    async def _call_azure(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import openai

        api_key = model.credentials.get("api_key")
        endpoint = model.credentials.get("endpoint")
        deployment = model.credentials.get("deployment_name")

        if not api_key or not endpoint or not deployment:
            raise ValidationException("Azure OpenAI credentials not fully configured")

        client = openai.AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version="2024-02-15-preview",
        )

        response = await client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=model.config.get("temperature", 0.1),
            max_tokens=model.config.get("max_tokens", 2000),
            response_format={"type": "json_object"} if model.config.get("json_mode", True) else None,
        )

        output_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        try:
            output_data = json.loads(output_text)
        except json.JSONDecodeError:
            output_data = {"raw_output": output_text}

        cost = (tokens_used / 1000) * 0.01

        return output_data, tokens_used, cost

    async def _call_huggingface(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import httpx

        api_key = model.credentials.get("api_key")
        model_id = model.credentials.get("model_id", model.model_name)

        if not api_key:
            raise ValidationException("Hugging Face API key not configured")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://api-inference.huggingface.co/models/{model_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"inputs": prompt, "parameters": {"return_full_text": False}},
                timeout=60.0,
            )

            if response.status_code != 200:
                raise ValidationException(f"Hugging Face API error: {response.text}")

            result = response.json()
            output_text = result[0].get("generated_text", "") if isinstance(result, list) else str(result)

            try:
                output_data = json.loads(output_text)
            except json.JSONDecodeError:
                output_data = {"raw_output": output_text}

            return output_data, 0, 0.0

    async def _process_with_ai(self, model: AIModel, document_text: str, request: dict) -> tuple[dict, int, float]:
        prompt = self._build_prompt(model, request, document_text)

        if model.provider == AIModelProvider.OPENAI:
            return await self._call_openai(model, prompt)
        elif model.provider == AIModelProvider.ANTHROPIC:
            return await self._call_anthropic(model, prompt)
        elif model.provider == AIModelProvider.GOOGLE:
            return await self._call_google(model, prompt)
        elif model.provider == AIModelProvider.AZURE:
            return await self._call_azure(model, prompt)
        elif model.provider == AIModelProvider.HUGGINGFACE:
            return await self._call_huggingface(model, prompt)
        else:
            raise ValidationException(f"Unsupported AI provider: {model.provider}")

    async def create_job(self, data: dict, tenant_id: UUID, created_by: UUID) -> AIProcessingJob:
        from app.modules.documents.models import Document
        doc_result = await self.db.execute(
            select(Document).where(Document.id == data["document_id"], Document.tenant_id == tenant_id)
        )
        if not doc_result.scalar_one_or_none():
            raise NotFoundException(detail="Document not found")

        model_result = await self.db.execute(
            select(AIModel).where(AIModel.id == data["model_id"], AIModel.tenant_id == tenant_id)
        )
        if not model_result.scalar_one_or_none():
            raise NotFoundException(detail="AI model not found")

        job = AIProcessingJob(
            **data,
            tenant_id=tenant_id,
            created_by=created_by,
            status=AIProcessingStatus.PENDING,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_job(self, job_id: UUID, tenant_id: UUID) -> AIProcessingJob:
        job = await self.job_repository.get_by_id(job_id, tenant_id)
        if not job:
            raise NotFoundException(detail="AI processing job not found")
        return job

    async def get_by_document(self, document_id: UUID, tenant_id: UUID) -> list:
        return await self.job_repository.get_by_document(document_id, tenant_id)

    async def list_jobs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        model_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list, int]:
        return await self.job_repository.get_all(tenant_id, page, page_size, status, model_id, date_from, date_to)

    async def _download_document(self, document: Document) -> bytes:
        azure_service = get_azure_blob_service()
        return await azure_service.download_blob(document.storage_key)

    async def _get_document_text(self, document: Document) -> str:
        if document.ocr_text:
            return document.ocr_text

        file_content = await self._download_document(document)

        if document.mime_type and document.mime_type.startswith("text/"):
            return file_content.decode("utf-8", errors="replace")

        return f"[Document: {document.filename}, size: {len(file_content)} bytes]"

    def _build_prompt(self, model: AIModel, request: dict, document_text: str) -> str:
        base_prompt = request.get("prompt", "")
        input_data = request.get("input_data", {})

        if model.model_type == AIModelType.CLASSIFICATION:
            prompt = f"""Classify the following document into one of the predefined categories.
Document text:
{document_text[:8000]}

Return a JSON object with:
- category: the classification category
- confidence: confidence score (0-1)
- reasoning: brief explanation"""

        elif model.model_type == AIModelType.EXTRACTION:
            fields = input_data.get("fields", [])
            fields_str = ", ".join(fields) if fields else "all relevant fields"
            prompt = f"""Extract the following fields from the document:
Fields to extract: {fields_str}

Document text:
{document_text[:8000]}

Return a JSON object with extracted field names as keys and their values. Include confidence scores for each field."""

        elif model.model_type == AIModelType.SUMMARIZATION:
            prompt = f"""Summarize the following document:
{document_text[:8000]}

Return a JSON object with:
- summary: concise summary
- key_points: list of key points
- confidence: confidence score (0-1)"""

        elif model.model_type == AIModelType.ENTITY_RECOGNITION:
            prompt = f"""Extract named entities from the following document:
{document_text[:8000]}

Return a JSON object with entities categorized by type (person, organization, location, date, etc.)"""

        else:
            prompt = base_prompt or f"Process the following document:\n{document_text[:8000]}"

        return prompt

    async def _call_openai(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import openai

        api_key = model.credentials.get("api_key")
        if not api_key:
            raise ValidationException("OpenAI API key not configured")

        client = openai.AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model=model.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=model.config.get("temperature", 0.1),
            max_tokens=model.config.get("max_tokens", 2000),
            response_format={"type": "json_object"} if model.config.get("json_mode", True) else None,
        )

        output_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        try:
            output_data = json.loads(output_text)
        except json.JSONDecodeError:
            output_data = {"raw_output": output_text}

        cost = (tokens_used / 1000) * 0.01

        return output_data, tokens_used, cost

    async def _call_anthropic(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import anthropic

        api_key = model.credentials.get("api_key")
        if not api_key:
            raise ValidationException("Anthropic API key not configured")

        client = anthropic.AsyncAnthropic(api_key=api_key)

        response = await client.messages.create(
            model=model.model_name,
            max_tokens=model.config.get("max_tokens", 2000),
            temperature=model.config.get("temperature", 0.1),
            messages=[{"role": "user", "content": prompt}],
        )

        output_text = response.content[0].text if response.content else ""
        tokens_used = response.usage.input_tokens + response.usage.output_tokens if response.usage else 0

        try:
            output_data = json.loads(output_text)
        except json.JSONDecodeError:
            output_data = {"raw_output": output_text}

        cost = (tokens_used / 1000) * 0.015

        return output_data, tokens_used, cost

    async def _call_google(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import google.generativeai as genai

        api_key = model.credentials.get("api_key")
        if not api_key:
            raise ValidationException("Google API key not configured")

        genai.configure(api_key=api_key)
        gm = genai.GenerativeModel(model.model_name)

        response = await gm.generate_content_async(prompt)
        output_text = response.text if response.text else ""
        tokens_used = 0

        try:
            output_data = json.loads(output_text)
        except json.JSONDecodeError:
            output_data = {"raw_output": output_text}

        cost = 0.0

        return output_data, tokens_used, cost

    async def _call_azure(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import openai

        api_key = model.credentials.get("api_key")
        endpoint = model.credentials.get("endpoint")
        deployment = model.credentials.get("deployment_name")

        if not api_key or not endpoint or not deployment:
            raise ValidationException("Azure OpenAI credentials not fully configured")

        client = openai.AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version="2024-02-15-preview",
        )

        response = await client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=model.config.get("temperature", 0.1),
            max_tokens=model.config.get("max_tokens", 2000),
            response_format={"type": "json_object"} if model.config.get("json_mode", True) else None,
        )

        output_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        try:
            output_data = json.loads(output_text)
        except json.JSONDecodeError:
            output_data = {"raw_output": output_text}

        cost = (tokens_used / 1000) * 0.01

        return output_data, tokens_used, cost

    async def _call_huggingface(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import httpx

        api_key = model.credentials.get("api_key")
        model_id = model.credentials.get("model_id", model.model_name)

        if not api_key:
            raise ValidationException("Hugging Face API key not configured")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://api-inference.huggingface.co/models/{model_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"inputs": prompt, "parameters": {"return_full_text": False}},
                timeout=60.0,
            )

            if response.status_code != 200:
                raise ValidationException(f"Hugging Face API error: {response.text}")

            result = response.json()
            output_text = result[0].get("generated_text", "") if isinstance(result, list) else str(result)

            try:
                output_data = json.loads(output_text)
            except json.JSONDecodeError:
                output_data = {"raw_output": output_text}

            return output_data, 0, 0.0

    async def _process_with_ai(self, model: AIModel, document_text: str, request: dict) -> tuple[dict, int, float]:
        prompt = self._build_prompt(model, request, document_text)

        if model.provider == AIModelProvider.OPENAI:
            return await self._call_openai(model, prompt)
        elif model.provider == AIModelProvider.ANTHROPIC:
            return await self._call_anthropic(model, prompt)
        elif model.provider == AIModelProvider.GOOGLE:
            return await self._call_google(model, prompt)
        elif model.provider == AIModelProvider.AZURE:
            return await self._call_azure(model, prompt)
        elif model.provider == AIModelProvider.HUGGINGFACE:
            return await self._call_huggingface(model, prompt)
        else:
            raise ValidationException(f"Unsupported AI provider: {model.provider}")

    async def create_job(self, data: dict, tenant_id: UUID, created_by: UUID) -> AIProcessingJob:
        from app.modules.documents.models import Document
        doc_result = await self.db.execute(
            select(Document).where(Document.id == data["document_id"], Document.tenant_id == tenant_id)
        )
        if not doc_result.scalar_one_or_none():
            raise NotFoundException(detail="Document not found")

        model_result = await self.db.execute(
            select(AIModel).where(AIModel.id == data["model_id"], AIModel.tenant_id == tenant_id)
        )
        if not model_result.scalar_one_or_none():
            raise NotFoundException(detail="AI model not found")

        job = AIProcessingJob(
            **data,
            tenant_id=tenant_id,
            created_by=created_by,
            status=AIProcessingStatus.PENDING,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_job(self, job_id: UUID, tenant_id: UUID) -> AIProcessingJob:
        job = await self.job_repository.get_by_id(job_id, tenant_id)
        if not job:
            raise NotFoundException(detail="AI processing job not found")
        return job

    async def get_by_document(self, document_id: UUID, tenant_id: UUID) -> list:
        return await self.job_repository.get_by_document(document_id, tenant_id)

    async def list_jobs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        model_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list, int]:
        return await self.job_repository.get_all(tenant_id, page, page_size, status, model_id, date_from, date_to)

    async def _download_document(self, document: Document) -> bytes:
        azure_service = get_azure_blob_service()
        return await azure_service.download_blob(document.storage_key)

    async def _get_document_text(self, document: Document) -> str:
        if document.ocr_text:
            return document.ocr_text

        file_content = await self._download_document(document)

        if document.mime_type and document.mime_type.startswith("text/"):
            return file_content.decode("utf-8", errors="replace")

        return f"[Document: {document.filename}, size: {len(file_content)} bytes]"

    def _build_prompt(self, model: AIModel, request: dict, document_text: str) -> str:
        base_prompt = request.get("prompt", "")
        input_data = request.get("input_data", {})

        if model.model_type == AIModelType.CLASSIFICATION:
            prompt = f"""Classify the following document into one of the predefined categories.
Document text:
{document_text[:8000]}

Return a JSON object with:
- category: the classification category
- confidence: confidence score (0-1)
- reasoning: brief explanation"""

        elif model.model_type == AIModelType.EXTRACTION:
            fields = input_data.get("fields", [])
            fields_str = ", ".join(fields) if fields else "all relevant fields"
            prompt = f"""Extract the following fields from the document:
Fields to extract: {fields_str}

Document text:
{document_text[:8000]}

Return a JSON object with extracted field names as keys and their values. Include confidence scores for each field."""

        elif model.model_type == AIModelType.SUMMARIZATION:
            prompt = f"""Summarize the following document:
{document_text[:8000]}

Return a JSON object with:
- summary: concise summary
- key_points: list of key points
- confidence: confidence score (0-1)"""

        elif model.model_type == AIModelType.ENTITY_RECOGNITION:
            prompt = f"""Extract named entities from the following document:
{document_text[:8000]}

Return a JSON object with entities categorized by type (person, organization, location, date, etc.)"""

        else:
            prompt = base_prompt or f"Process the following document:\n{document_text[:8000]}"

        return prompt

    async def _call_openai(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import openai

        api_key = model.credentials.get("api_key")
        if not api_key:
            raise ValidationException("OpenAI API key not configured")

        client = openai.AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model=model.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=model.config.get("temperature", 0.1),
            max_tokens=model.config.get("max_tokens", 2000),
            response_format={"type": "json_object"} if model.config.get("json_mode", True) else None,
        )

        output_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        try:
            output_data = json.loads(output_text)
        except json.JSONDecodeError:
            output_data = {"raw_output": output_text}

        cost = (tokens_used / 1000) * 0.01

        return output_data, tokens_used, cost

    async def _call_anthropic(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import anthropic

        api_key = model.credentials.get("api_key")
        if not api_key:
            raise ValidationException("Anthropic API key not configured")

        client = anthropic.AsyncAnthropic(api_key=api_key)

        response = await client.messages.create(
            model=model.model_name,
            max_tokens=model.config.get("max_tokens", 2000),
            temperature=model.config.get("temperature", 0.1),
            messages=[{"role": "user", "content": prompt}],
        )

        output_text = response.content[0].text if response.content else ""
        tokens_used = response.usage.input_tokens + response.usage.output_tokens if response.usage else 0

        try:
            output_data = json.loads(output_text)
        except json.JSONDecodeError:
            output_data = {"raw_output": output_text}

        cost = (tokens_used / 1000) * 0.015

        return output_data, tokens_used, cost

    async def _call_google(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import google.generativeai as genai

        api_key = model.credentials.get("api_key")
        if not api_key:
            raise ValidationException("Google API key not configured")

        genai.configure(api_key=api_key)
        gm = genai.GenerativeModel(model.model_name)

        response = await gm.generate_content_async(prompt)
        output_text = response.text if response.text else ""
        tokens_used = 0

        try:
            output_data = json.loads(output_text)
        except json.JSONDecodeError:
            output_data = {"raw_output": output_text}

        cost = 0.0

        return output_data, tokens_used, cost

    async def _call_azure(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import openai

        api_key = model.credentials.get("api_key")
        endpoint = model.credentials.get("endpoint")
        deployment = model.credentials.get("deployment_name")

        if not api_key or not endpoint or not deployment:
            raise ValidationException("Azure OpenAI credentials not fully configured")

        client = openai.AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version="2024-02-15-preview",
        )

        response = await client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=model.config.get("temperature", 0.1),
            max_tokens=model.config.get("max_tokens", 2000),
            response_format={"type": "json_object"} if model.config.get("json_mode", True) else None,
        )

        output_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        try:
            output_data = json.loads(output_text)
        except json.JSONDecodeError:
            output_data = {"raw_output": output_text}

        cost = (tokens_used / 1000) * 0.01

        return output_data, tokens_used, cost

    async def _call_huggingface(self, model: AIModel, prompt: str) -> tuple[dict, int, float]:
        import httpx

        api_key = model.credentials.get("api_key")
        model_id = model.credentials.get("model_id", model.model_name)

        if not api_key:
            raise ValidationException("Hugging Face API key not configured")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://api-inference.huggingface.co/models/{model_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"inputs": prompt, "parameters": {"return_full_text": False}},
                timeout=60.0,
            )

            if response.status_code != 200:
                raise ValidationException(f"Hugging Face API error: {response.text}")

            result = response.json()
            output_text = result[0].get("generated_text", "") if isinstance(result, list) else str(result)

            try:
                output_data = json.loads(output_text)
            except json.JSONDecodeError:
                output_data = {"raw_output": output_text}

            return output_data, 0, 0.0

    async def _process_with_ai(self, model: AIModel, document_text: str, request: dict) -> tuple[dict, int, float]:
        prompt = self._build_prompt(model, request, document_text)

        if model.provider == AIModelProvider.OPENAI:
            return await self._call_openai(model, prompt)
        elif model.provider == AIModelProvider.ANTHROPIC:
            return await self._call_anthropic(model, prompt)
        elif model.provider == AIModelProvider.GOOGLE:
            return await self._call_google(model, prompt)
        elif model.provider == AIModelProvider.AZURE:
            return await self._call_azure(model, prompt)
        elif model.provider == AIModelProvider.HUGGINGFACE:
            return await self._call_huggingface(model, prompt)
        else:
            raise ValidationException(f"Unsupported AI provider: {model.provider}")

    async def create_job(self, data: dict, tenant_id: UUID, created_by: UUID) -> AIProcessingJob:
        from app.modules.documents.models import Document
        doc_result = await self.db.execute(
            select(Document).where(Document.id == data["document_id"], Document.tenant_id == tenant_id)
        )
        if not doc_result.scalar_one_or_none():
            raise NotFoundException(detail="Document not found")

        model_result = await self.db.execute(
            select(AIModel).where(AIModel.id == data["model_id"], AIModel.tenant_id == tenant_id)
        )
        if not model_result.scalar_one_or_none():
            raise NotFoundException(detail="AI model not found")

        job = AIProcessingJob(
            **data,
            tenant_id=tenant_id,
            created_by=created_by,
            status=AIProcessingStatus.PENDING,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_job(self, job_id: UUID, tenant_id: UUID) -> AIProcessingJob:
        job = await self.job_repository.get_by_id(job_id, tenant_id)
        if not job:
            raise NotFoundException(detail="AI processing job not found")
        return job

    async def get_by_document(self, document_id: UUID, tenant_id: UUID) -> list:
        return await self.job_repository.get_by_document(document_id, tenant_id)

    async def list_jobs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        model_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list, int]:
        return await self.job_repository.get_all(tenant_id, page, page_size, status, model_id, date_from, date_to)

    async def process_document(self, request: dict, tenant_id: UUID, processed_by: UUID) -> AIProcessingJob:
        from app.modules.documents.models import Document
        doc_result = await self.db.execute(
            select(Document).where(Document.id == request["document_id"], Document.tenant_id == tenant_id)
        )
        document = doc_result.scalar_one_or_none()
        if not document:
            raise NotFoundException(detail="Document not found")

        model_id = request.get("model_id")
        if not model_id:
            raise ValueError("Model ID is required")

        model_result = await self.db.execute(
            select(AIModel).where(AIModel.id == model_id, AIModel.tenant_id == tenant_id)
        )
        model = model_result.scalar_one_or_none()
        if not model:
            raise NotFoundException(detail="AI model not found")

        if not model.is_active:
            raise ValidationException("AI model is not active")

        job = AIProcessingJob(
            document_id=request["document_id"],
            model_id=model_id,
            prompt=request.get("prompt"),
            input_data=request.get("input_data", {}),
            tenant_id=tenant_id,
            created_by=processed_by,
            status=AIProcessingStatus.PENDING,
        )
        self.db.add(job)
        await self.db.flush()

        job.status = AIProcessingStatus.PROCESSING
        job.started_at = datetime.now()
        await self.db.flush()

        try:
            document_text = await self._get_document_text(document)

            output_data, tokens_used, cost = await self._process_with_ai(model, document_text, request)

            job.status = AIProcessingStatus.COMPLETED
            job.completed_at = datetime.now()
            job.output_data = output_data
            job.confidence_score = output_data.get("confidence", 0.9) if isinstance(output_data, dict) else 0.9
            job.processing_time_ms = int((job.completed_at - job.started_at).total_seconds() * 1000) if job.started_at else 0
            job.tokens_used = tokens_used
            job.cost = cost

        except ValidationException as e:
            job.status = AIProcessingStatus.FAILED
            job.completed_at = datetime.now()
            job.error_message = str(e)
            job.processing_time_ms = int((datetime.now() - job.started_at).total_seconds() * 1000) if job.started_at else 0
        except Exception as e:
            job.status = AIProcessingStatus.FAILED
            job.completed_at = datetime.now()
            job.error_message = f"Unexpected error: {str(e)}"
            job.processing_time_ms = int((datetime.now() - job.started_at).total_seconds() * 1000) if job.started_at else 0

        await self.db.flush()
        await self.db.refresh(job)

        return job

    async def get_job(self, job_id: UUID, tenant_id: UUID) -> AIProcessingJob:
        job = await self.job_repository.get_by_id(job_id, tenant_id)
        if not job:
            raise NotFoundException(detail="AI processing job not found")
        return job

    async def list_jobs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        model_id: UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> tuple[list, int]:
        return await self.job_repository.get_all(tenant_id, page, page_size, status, model_id, date_from, date_to)

    async def retry_job(self, job_id: UUID, tenant_id: UUID) -> AIProcessingJob:
        job = await self.job_repository.get_by_id(job_id, tenant_id)
        if not job:
            raise NotFoundException(detail="Job not found")

        if job.status not in [AIProcessingStatus.FAILED, AIProcessingStatus.PENDING]:
            raise ValueError("Can only retry failed or pending jobs")

        job.status = AIProcessingStatus.PENDING
        job.retry_count += 1
        job.error_message = None
        await self.db.flush()
        await self.db.refresh(job)
        return job


class AIConfidenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AIConfidenceThresholdRepository(db)

    async def create_threshold(self, data: dict, tenant_id: UUID, created_by: UUID) -> AIConfidenceThreshold:
        threshold = AIConfidenceThreshold(
            **data,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        self.db.add(threshold)
        await self.db.flush()
        await self.db.refresh(threshold)
        return threshold

    async def get_by_type(self, model_type: str, tenant_id: UUID) -> AIConfidenceThreshold | None:
        return await self.repository.get_by_type(model_type, tenant_id)

    async def get_all(self, tenant_id: UUID) -> list:
        return await self.repository.get_all(tenant_id)

    async def update(self, threshold_id: UUID, tenant_id: UUID, data: dict, updated_by: UUID) -> AIConfidenceThreshold:
        threshold = await self.repository.get_by_type(threshold_id, tenant_id)
        if not threshold:
            raise NotFoundException(detail="Threshold not found")

        for field, value in data.items():
            if hasattr(threshold, field):
                setattr(threshold, field, value)

        threshold.updated_at = datetime.now()
        await self.db.flush()
        await self.db.refresh(threshold)
        return threshold

    async def evaluate_confidence(self, model_type: str, tenant_id: UUID, confidence: float) -> dict:
        threshold = await self.get_by_type(model_type, tenant_id)
        if not threshold:
            return {"action": "review", "reason": "No threshold configured"}

        if confidence >= threshold.auto_approve_threshold:
            return {"action": threshold.auto_approve_action, "threshold": threshold.auto_approve_threshold}
        elif confidence <= threshold.auto_reject_threshold:
            return {"action": threshold.auto_reject_action, "threshold": threshold.auto_reject_threshold}
        else:
            return {"action": threshold.requires_review_action, "threshold": threshold.requires_review_threshold}


class AIReviewTaskService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AIReviewTaskRepository(db)
        self.job_repository = AIProcessingJobRepository(db)

    async def create_task(self, job_id: UUID, tenant_id: UUID, assignee_id: UUID | None, created_by: UUID) -> AIReviewTask:
        job = await self.job_repository.get_by_id(job_id, tenant_id)
        if not job:
            raise NotFoundException(detail="AI processing job not found")

        task = AIReviewTask(
            job_id=job_id,
            assignee_id=assignee_id,
            tenant_id=tenant_id,
            created_by=created_by,
            status="pending",
            original_confidence=job.confidence_score,
        )
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def get_task(self, task_id: UUID, tenant_id: UUID) -> AIReviewTask:
        task = await self.repository.get_by_id(task_id, tenant_id)
        if not task:
            raise NotFoundException(detail="Review task not found")
        return task

    async def list_tasks(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        assignee_id: UUID | None = None,
    ) -> tuple[list, int]:
        return await self.repository.get_all(tenant_id, page, page_size, status, assignee_id)

    async def update_task(
        self, task_id: UUID, tenant_id: UUID, data: dict, updated_by: UUID
    ) -> AIReviewTask:
        task = await self.repository.get_by_id(task_id, tenant_id)
        if not task:
            raise NotFoundException(detail="Review task not found")

        update_data = {k: v for k, v in data.items() if v is not None}
        
        for field, value in update_data.items():
            if hasattr(task, field):
                setattr(task, field, value)

        if "status" in update_data and task.status != update_data["status"]:
            if update_data["status"] == "in_progress" and task.status == "pending":
                task.started_at = datetime.now()
            elif update_data["status"] in ["completed", "approved", "rejected"]:
                task.completed_at = datetime.now()
                if "action_taken" in update_data:
                    task.action_taken = update_data["action_taken"]
                if "final_confidence" in update_data:
                    task.final_confidence = update_data["final_confidence"]

        task.updated_at = datetime.now()
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def get_task(self, task_id: UUID, tenant_id: UUID) -> AIReviewTask:
        task = await self.repository.get_by_id(task_id, tenant_id)
        if not task:
            raise NotFoundException(detail="Review task not found")
        return task