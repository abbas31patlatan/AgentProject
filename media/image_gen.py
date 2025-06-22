# File: media/image_gen.py

from typing import Any, Optional, Dict
import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

class ImageGenerator:
    """
    Metinden hızlı ve kaliteli görsel üretimi:
    - Stable Diffusion ve SDXL desteği
    - Özelleştirilebilir çözünürlük, prompt, seed, negative prompt
    - Otomatik GPU/CPU tespiti
    """

    def __init__(
        self,
        model_name: str = "stabilityai/stable-diffusion-2-1",
        device: Optional[str] = None,
        use_fp16: bool = True
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name = model_name
        self.use_fp16 = use_fp16 and torch.cuda.is_available()
        self.pipe = StableDiffusionPipeline.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if self.use_fp16 else torch.float32,
        ).to(self.device)
        self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(self.pipe.scheduler.config)

    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 30,
        seed: Optional[int] = None,
        guidance_scale: float = 7.5,
        return_image: bool = True
    ) -> Any:
        """
        Metinden bir veya daha fazla görsel üretir.
        """
        generator = torch.manual_seed(seed) if seed is not None else None
        with torch.autocast(self.device):
            result = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
            )
        if return_image:
            return result.images[0]
        return result

    def save_image(self, image, path: str):
        image.save(path)

    def generate_and_save(
        self,
        prompt: str,
        out_path: str,
        **kwargs
    ):
        image = self.generate(prompt, **kwargs)
        self.save_image(image, out_path)
        return out_path
