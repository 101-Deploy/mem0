from typing import Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter

from embedchain.embedchain.chunkers.base_chunker import BaseChunker
from embedchain.embedchain.config.add_config import ChunkerConfig
from embedchain.embedchain.helpers.json_serializable import register_deserializable


@register_deserializable
class BeehiivChunker(BaseChunker):
    """Chunker for Beehiiv."""

    def __init__(self, config: Optional[ChunkerConfig] = None):
        if config is None:
            config = ChunkerConfig(chunk_size=1000, chunk_overlap=0, length_function=len)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=config.length_function,
        )
        super().__init__(text_splitter)
