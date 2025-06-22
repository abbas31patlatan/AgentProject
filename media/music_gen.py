# File: media/music_gen.py

from typing import Any, Optional
import torch

try:
    from audiocraft.models import MusicGen
except ImportError:
    MusicGen = None  # MusicGen paketini ayrıca kurman gerekebilir

class MusicGenerator:
    """
    Metinden ve kısa açıklamadan müzik besteler.
    - MusicGen (facebookresearch/audiocraft) tabanlı
    - Farklı model ağırlıkları: melody, small, medium, large
    - Kendi seed, süre, bpm gibi parametrelerini ayarlayabilirsin
    """

    def __init__(
        self,
        model_name: str = "facebook/musicgen-melody",
        device: Optional[str] = None
    ):
        if MusicGen is None:
            raise ImportError("MusicGen modülü yüklü değil! (pip install audiocraft)")
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = MusicGen.get_pretrained(model_name).to(self.device)

    def generate(
        self,
        prompt: str,
        duration: int = 8,
        sample_rate: int = 32000,
        progress_callback: Optional[Any] = None
    ) -> Any:
        """
        Belirtilen prompta göre müzik üretir (wav/audio).
        """
        output = self.model.generate(
            descriptions=[prompt],
            progress=progress_callback,
            return_tokens=False,
            durations=[duration],
            sampling_rate=sample_rate
        )
        # output: { 'wav': np.ndarray, ... }
        return output['wav'][0]

    def save_wav(self, wav, path: str, sample_rate: int = 32000):
        import soundfile as sf
        sf.write(path, wav, samplerate=sample_rate)

    def generate_and_save(
        self,
        prompt: str,
        out_path: str,
        duration: int = 8,
        sample_rate: int = 32000
    ):
        wav = self.generate(prompt, duration=duration, sample_rate=sample_rate)
        self.save_wav(wav, out_path, sample_rate=sample_rate)
        return out_path
