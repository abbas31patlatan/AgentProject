# File: core/context_stitcher.py

from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer, util
import numpy as np

class ContextStitcher:
    """
    Çok uzun konuşma ve kod geçmişinden anlık olarak en anlamlı context'i seçip özetleyerek AI’ye “unutmayan zihin” verir.
    - Vektör tabanlı semantik arama
    - Otomatik özetleme ve önemli olay seçimi
    - Kendi başına geçmişi özetleyip “patch” olarak modele sunar
    """

    def __init__(
        self,
        memory_manager,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.memory = memory_manager
        self.embedder = SentenceTransformer(embedding_model_name)

    def retrieve_context_patch(
        self,
        query: str,
        max_context_tokens: int = 1024,
        max_patches: int = 8
    ) -> str:
        """
        Kullanıcı talebine göre geçmişten en alakalı konuşma/kod parçalarını seçer ve özetler.
        """
        # 1. Tüm geçmişi vektörle
        records = self.memory.get_all_interactions(limit=1000)
        texts = [f"Kullanıcı: {r['prompt']}\nAI: {r['response']}" for r in records]
        if not texts:
            return ""
        embeddings = self.embedder.encode(texts, convert_to_tensor=True)
        query_vec = self.embedder.encode([query], convert_to_tensor=True)[0]

        # 2. En yakın N tanesini seç
        similarities = util.cos_sim(query_vec, embeddings)[0].cpu().numpy()
        idx_sorted = np.argsort(-similarities)[:max_patches]
        selected = [texts[i] for i in idx_sorted]

        # 3. Token sayısı aşılırsa otomatik kırp/özetle
        patch = ""
        token_count = 0
        for s in selected:
            est_tokens = len(s.split())
            if token_count + est_tokens > max_context_tokens:
                break
            patch += s + "\n"
            token_count += est_tokens
        return patch.strip()

    def summarize_context(self, patch: str, summarizer_model = None) -> str:
        """
        Çok uzun contextleri özetler (isteğe bağlı transformer ile).
        """
        if summarizer_model:
            return summarizer_model(patch)
        # Basit fallback: ilk ve son 2 cümleyi birleştir
        lines = patch.splitlines()
        if len(lines) < 5:
            return patch
        return "\n".join(lines[:2] + ["..."] + lines[-2:])

# MemoryManager'a küçük ek:
# File: core/memory.py → MemoryManager

    def get_all_interactions(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Son N konuşmayı/kod etkileşimini kronolojik döndürür.
        """
        with self._lock, self._conn:
            cur = self._conn.execute(
                "SELECT prompt, response FROM interactions ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            rows = cur.fetchall()
        return list(reversed([dict(row) for row in rows]))
