"""
AI Engine for LOSTFOUND - Image Embedding and Similarity Search
Uses OpenAI CLIP (openai/clip-vit-base-patch32) with FAISS indexing.
Includes robust fallback to NumPy cosine similarity if PyTorch/Transformers fail.
"""

import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

# Try to import PyTorch and Transformers
try:
    import torch
    from PIL import Image
    from transformers import CLIPProcessor, CLIPModel
    import faiss
    
    _TORCH_AVAILABLE = True
    _FAISS_AVAILABLE = True
    
    # Initialize CLIP model and processor (lazy loading)
    _clip_model = None
    _clip_processor = None
    
    def _load_clip_model():
        """Lazy load CLIP model and processor."""
        global _clip_model, _clip_processor
        if _clip_model is None or _clip_processor is None:
            _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        return _clip_model, _clip_processor

except ImportError:
    _TORCH_AVAILABLE = False
    _FAISS_AVAILABLE = False
    _clip_model = None
    _clip_processor = None

# Try to import FAISS
try:
    import faiss
    _FAISS_AVAILABLE = True
except ImportError:
    _FAISS_AVAILABLE = False

logger = logging.getLogger(__name__)


def extract_image_embedding(image_path: str) -> Optional[List[float]]:
    """
    Extract image embedding using CLIP model.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        JSON-serializable list of floats representing the embedding,
        or None if extraction fails
    """
    if not _TORCH_AVAILABLE:
        logger.warning("PyTorch/Transformers not available, using fallback")
        return _fallback_extract_embedding(image_path)
    
    try:
        model, processor = _load_clip_model()
        
        # Load and preprocess image
        image = Image.open(image_path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt", padding=True)
        
        # Generate embedding
        with torch.no_grad():
            outputs = model.get_image_features(**inputs)
            embedding = outputs.cpu().numpy().flatten()
            
        # Normalize embedding
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        
        # Convert to JSON-serializable list
        return embedding.tolist()
        
    except Exception as e:
        logger.error(f"Error extracting embedding with CLIP: {e}")
        return _fallback_extract_embedding(image_path)


def _fallback_extract_embedding(image_path: str) -> Optional[List[float]]:
    """
    Fallback embedding extraction using simple image statistics.
    This is a basic fallback when CLIP is not available.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        JSON-serializable list of floats representing a basic embedding
    """
    try:
        from PIL import Image
        
        image = Image.open(image_path).convert("RGB")
        image = image.resize((224, 224))  # Standard size
        
        # Convert to numpy array
        img_array = np.array(image, dtype=np.float32)
        
        # Extract basic features: color histograms and mean values
        features = []
        
        # RGB mean values
        for channel in range(3):
            features.append(np.mean(img_array[:, :, channel]))
            features.append(np.std(img_array[:, :, channel]))
        
        # Color histogram for each channel (64 bins per channel)
        for channel in range(3):
            hist, _ = np.histogram(img_array[:, :, channel], bins=64, range=(0, 255))
            hist = hist.astype(np.float32) / (hist.sum() + 1e-8)
            features.extend(hist.tolist())
        
        # Resize image to smaller size and flatten for additional features
        small_img = image.resize((8, 8))
        small_array = np.array(small_img, dtype=np.float32)
        features.extend(small_array.flatten().tolist())
        
        # Normalize features
        features_array = np.array(features, dtype=np.float32)
        features_array = features_array / (np.linalg.norm(features_array) + 1e-8)
        
        return features_array.tolist()
        
    except Exception as e:
        logger.error(f"Error in fallback embedding extraction: {e}")
        return None


def create_faiss_index(embeddings: List[List[float]]) -> Optional[Any]:
    """
    Create a FAISS index from a list of embeddings.
    
    Args:
        embeddings: List of embedding vectors (each vector is a list of floats)
        
    Returns:
        FAISS index object, or None if creation fails
    """
    if not embeddings:
        return None
    
    if not _FAISS_AVAILABLE:
        logger.warning("FAISS not available, returning None")
        return None
    
    try:
        # Convert to numpy array
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # Get dimension
        dimension = embeddings_array.shape[1]
        
        # Create index (using Inner Product for cosine similarity after normalization)
        index = faiss.IndexFlatIP(dimension)
        
        # Add embeddings to index
        index.add(embeddings_array)
        
        return index
        
    except Exception as e:
        logger.error(f"Error creating FAISS index: {e}")
        return None


def search_similar_images(
    query_embedding: List[float],
    stored_embeddings: List[List[float]],
    case_ids: List[int],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Search for similar images using FAISS or NumPy fallback.
    
    Args:
        query_embedding: The query embedding vector
        stored_embeddings: List of stored embedding vectors
        case_ids: List of case IDs corresponding to stored embeddings
        top_k: Number of top results to return
        
    Returns:
        List of dictionaries with 'case_id' and 'similarity_score'
    """
    if not query_embedding or not stored_embeddings or not case_ids:
        return []
    
    # Ensure top_k doesn't exceed available embeddings
    top_k = min(top_k, len(stored_embeddings))
    
    if _FAISS_AVAILABLE and len(stored_embeddings) > 0:
        try:
            # Create index
            index = create_faiss_index(stored_embeddings)
            if index is None:
                return _numpy_similarity_search(query_embedding, stored_embeddings, case_ids, top_k)
            
            # Convert query to numpy array
            query_array = np.array([query_embedding], dtype=np.float32)
            
            # Search
            similarities, indices = index.search(query_array, top_k)
            
            # Build results
            results = []
            for i, (sim, idx) in enumerate(zip(similarities[0], indices[0])):
                if idx < len(case_ids):
                    results.append({
                        'case_id': case_ids[idx],
                        'similarity_score': float(sim),
                        'rank': i + 1
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in FAISS search: {e}")
            return _numpy_similarity_search(query_embedding, stored_embeddings, case_ids, top_k)
    else:
        return _numpy_similarity_search(query_embedding, stored_embeddings, case_ids, top_k)


def _numpy_similarity_search(
    query_embedding: List[float],
    stored_embeddings: List[List[float]],
    case_ids: List[int],
    top_k: int
) -> List[Dict[str, Any]]:
    """
    Fallback similarity search using NumPy cosine similarity.
    
    Args:
        query_embedding: The query embedding vector
        stored_embeddings: List of stored embedding vectors
        case_ids: List of case IDs corresponding to stored embeddings
        top_k: Number of top results to return
        
    Returns:
        List of dictionaries with 'case_id' and 'similarity_score'
    """
    try:
        # Convert to numpy arrays
        query_array = np.array(query_embedding, dtype=np.float32)
        stored_array = np.array(stored_embeddings, dtype=np.float32)
        
        # Normalize vectors (in case they're not already normalized)
        query_norm = query_array / (np.linalg.norm(query_array) + 1e-8)
        stored_norms = stored_array / (np.linalg.norm(stored_array, axis=1, keepdims=True) + 1e-8)
        
        # Calculate cosine similarities
        similarities = np.dot(stored_norms, query_norm)
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Build results
        results = []
        for rank, idx in enumerate(top_indices):
            if idx < len(case_ids):
                results.append({
                    'case_id': case_ids[idx],
                    'similarity_score': float(similarities[idx]),
                    'rank': rank + 1
                })
        
        return results
        
    except Exception as e:
        logger.error(f"Error in NumPy similarity search: {e}")
        return []


def calculate_similarity_between_embeddings(
    embedding1: List[float],
    embedding2: List[float]
) -> float:
    """
    Calculate cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        Cosine similarity score (float between -1 and 1)
    """
    try:
        vec1 = np.array(embedding1, dtype=np.float32)
        vec2 = np.array(embedding2, dtype=np.float32)
        
        # Normalize
        vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-8)
        vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-8)
        
        # Calculate cosine similarity
        similarity = float(np.dot(vec1_norm, vec2_norm))
        
        return similarity
        
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        return 0.0


def batch_extract_embeddings(image_paths: List[str]) -> List[Optional[List[float]]]:
    """
    Extract embeddings for multiple images.
    
    Args:
        image_paths: List of image file paths
        
    Returns:
        List of embeddings (some may be None if extraction fails)
    """
    embeddings = []
    for path in image_paths:
        emb = extract_image_embedding(path)
        embeddings.append(emb)
    return embeddings


def get_model_status() -> Dict[str, bool]:
    """
    Get the status of AI model components.
    
    Returns:
        Dictionary with status of each component
    """
    return {
        'torch_available': _TORCH_AVAILABLE,
        'faiss_available': _FAISS_AVAILABLE,
        'clip_loaded': _clip_model is not None and _clip_processor is not None
    }
