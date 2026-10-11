#!/usr/bin/env python3
"""
Generate embeddings for property descriptions.

This script generates 768-dimension embeddings for all properties in the database
that don't already have embeddings. The embeddings are used for semantic search.

For now, this uses placeholder embeddings. In Phase 4+ (search), this will be
replaced with actual embedding generation using an AI model.

Usage:
    python scripts/embed_properties.py [--force]

Options:
    --force: Regenerate embeddings even if they already exist
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse

import numpy as np
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.property import Property


def generate_placeholder_embedding(text: str, dimension: int = 768) -> list[float]:
    """
    Generate a placeholder embedding for text.
    
    In production, this will be replaced with actual embedding generation
    using an AI model (e.g., sentence-transformers, OpenAI, etc.).
    
    For now, this generates a deterministic embedding based on text hash
    for testing purposes.
    
    Args:
        text: Text to embed
        dimension: Embedding dimension (default: 768)
    
    Returns:
        List of floats representing the embedding
    """
    # Use text hash as seed for reproducibility
    seed = hash(text) % (2**32)
    np.random.seed(seed)
    
    # Generate random unit vector
    embedding = np.random.randn(dimension)
    
    # Normalize to unit length (common for embeddings)
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    
    return embedding.tolist()


def create_property_text(property_obj: Property) -> str:
    """
    Create searchable text from property attributes.
    
    This combines key property information into a single text that
    can be embedded for semantic search.
    
    Args:
        property_obj: Property object
    
    Returns:
        Combined text representation
    """
    parts = [
        property_obj.title,
        property_obj.description,
        f"{property_obj.property_type.value} for {property_obj.listing_type.value}",
        f"{property_obj.bedrooms} bedrooms",
        f"{property_obj.bathrooms} bathrooms",
        f"{property_obj.size_sqft} square feet",
        property_obj.location,
        property_obj.community,
        "furnished" if property_obj.furnished else "unfurnished",
    ]
    
    # Add amenities
    if property_obj.amenities:
        amenity_names = [amenity.name for amenity in property_obj.amenities]
        parts.append("amenities: " + ", ".join(amenity_names))
    
    return " | ".join(parts)


def embed_properties(db: Session, force: bool = False) -> tuple[int, int]:
    """
    Generate embeddings for properties in the database.
    
    Args:
        db: Database session
        force: If True, regenerate embeddings even if they exist
    
    Returns:
        Tuple of (total_properties, embedded_properties)
    """
    print("=" * 60)
    print("Property Embedding Generation")
    print("=" * 60)
    
    # Get properties
    if force:
        properties = db.query(Property).all()
        print(f"\n🔄 Force mode: Processing all {len(properties)} properties")
    else:
        properties = db.query(Property).filter(Property.embedding == None).all()
        print(f"\n📊 Found {len(properties)} properties without embeddings")
    
    if not properties:
        print("\n✅ No properties to process")
        return (0, 0)
    
    # Generate embeddings
    embedded_count = 0
    
    for i, property_obj in enumerate(properties, 1):
        try:
            # Create text representation
            text = create_property_text(property_obj)
            
            # Generate embedding
            embedding = generate_placeholder_embedding(text)
            
            # Update property
            property_obj.embedding = embedding
            
            embedded_count += 1
            
            if i % 10 == 0 or i == len(properties):
                print(f"  Progress: {i}/{len(properties)} properties processed")
        
        except Exception as e:
            print(f"  ⚠️  Error processing property {property_obj.reference}: {e}")
            continue
    
    # Commit changes
    try:
        db.commit()
        print(f"\n✅ Successfully embedded {embedded_count} properties")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error saving embeddings: {e}")
        import traceback
        traceback.print_exc()
        return (len(properties), 0)
    
    print("=" * 60)
    
    return (len(properties), embedded_count)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate embeddings for property descriptions"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate embeddings even if they already exist"
    )
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        total, embedded = embed_properties(db, force=args.force)
        
        if embedded == total or (not args.force and embedded > 0):
            sys.exit(0)
        else:
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
