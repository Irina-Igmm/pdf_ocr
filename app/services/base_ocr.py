from abc import ABC, abstractmethod
from typing import Union

import numpy as np
from PIL import Image

ImageInput = Union[np.ndarray, Image.Image, str, bytes]


class BaseOCRExtractor(ABC):
    """Common interface for all OCR backends."""

    @abstractmethod
    def extract_text(
        self,
        image: Union[ImageInput, "list[ImageInput]"],
        lang_list: list[str] | None = None,
        country_code: str | None = None,
    ) -> str:
        """Run OCR on a single image or a list of images (multi-page PDF).

        Args:
            image: PIL Image, numpy array, file path (str), bytes,
                   or a list of any of the above for multi-page PDFs.
            lang_list: Backend-specific language codes. When None,
                       inferred from country_code.
            country_code: ISO country code (e.g. "de", "fr") used to
                          look up lang_list when lang_list is None.

        Returns:
            Extracted text as a single string. Multi-page output is
            delimited by "--- Page N ---" markers.
        """
        ...

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Human-readable backend identifier used in log messages."""
        ...
