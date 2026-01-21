"""
Custom LangChain wrapper for OpenAI Responses API (gpt-5-nano).
Simpler implementation without complex Pydantic inheritance.
"""
import asyncio
from typing import Any, AsyncIterator, Iterator, List, Optional

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.llms import LLM
from langchain_core.outputs import GenerationChunk
from openai import OpenAI


class GPT5NanoLLM(LLM):
    """
    Custom LangChain LLM wrapper for OpenAI gpt-5-nano using Responses API.
    """
    
    api_key: str
    model: str = "gpt-5-nano"
    reasoning_effort: str = "minimal"
    max_output_tokens: int = 1000
    
    _client: Optional[OpenAI] = None
    
    class Config:
        underscore_attrs_are_private = True
    
    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        return self._client
    
    @property
    def _llm_type(self) -> str:
        return "gpt-5-nano"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the Responses API."""
        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                reasoning={"effort": self.reasoning_effort},
                max_output_tokens=self.max_output_tokens,
            )
            
            # Extract text from response
            return response.output[0].content
            
        except Exception as e:
            print(f"[GPT5NanoLLM ERROR] {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def _stream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[GenerationChunk]:
        """Sync stream - get full response then yield words."""
        try:
            text = self._call(prompt, stop, run_manager, **kwargs)
            
            # Simulate streaming by yielding words
            words = text.split()
            for word in words:
                token = word + " "
                chunk = GenerationChunk(text=token)
                if run_manager:
                    run_manager.on_llm_new_token(token, chunk=chunk)
                yield chunk
                
        except Exception as e:
            print(f"[GPT5NanoLLM STREAM ERROR] {e}")
            import traceback
            traceback.print_exc()
            yield GenerationChunk(text="")
    
    async def _astream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[GenerationChunk]:
        """Async stream - run sync call in thread then yield words."""
        try:
            # Run blocking call in thread pool
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                None, 
                lambda: self._call(prompt, stop, None, **kwargs)
            )
            
            # Simulate streaming by yielding words
            words = text.split() if text else []
            for word in words:
                token = word + " "
                chunk = GenerationChunk(text=token)
                if run_manager:
                    await run_manager.on_llm_new_token(token, chunk=chunk)
                yield chunk
                # Small delay to simulate streaming
                await asyncio.sleep(0.01)
                
        except Exception as e:
            print(f"[GPT5NanoLLM ASTREAM ERROR] {e}")
            import traceback
            traceback.print_exc()
            yield GenerationChunk(text="")
    
    @property
    def _identifying_params(self) -> dict:
        """Return identifying parameters."""
        return {
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "max_output_tokens": self.max_output_tokens,
        }
