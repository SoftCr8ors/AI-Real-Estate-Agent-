command for phase 3:
python -m pytest -v


  📚 Interactive API Documentation:
  
  http://127.0.0.1:8000/docs
   

#and also open docker and run this command 
docker-compose up -d
  
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  
  What to Test:
  
  1. Health Check ✅
  - Click on GET /health
  - Click "Try it out" → "Execute"
  - Should return {"status": "healthy", ...}
  
  2. Property Search 🔍
  - Click on POST /properties/search
  - Click "Try it out"
  - Try these example searches:
  
  Example 1: Basic Search
  
  {
    "listing_type": "buy",
    "location": "Dubai Marina",
    "bedrooms": 2,
    "max_price": 1500000
  }
  
  Example 2: With Amenities
  
  {
    "listing_type": "buy",
    "location": "marina",
    "bedrooms": 2,
    "max_price": 1500000,
    "amenities": ["Swimming Pool", "Gym"]
  }
  
  Example 3: Test Normalization
  
  {
    "listing_type": "buy",
    "location": "marina",
    "bedrooms": 2,
    "max_price": "1.5M"
  }
  
  3. Get Property Details 🏠
  - Click on GET /properties/{property_id}
  - Try property ID: 1
  
  4. Check Availability 📋
  - Click on GET /properties/{property_id}/availability
  - Try property ID: 1
  
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  
  What You Should See:
  
  ✅ Match scores (0-100) for each property
  ✅ Properties sorted by score
  ✅ Over-budget flag on expensive properties
  ✅ Primary images displayed
  ✅ Amenities list
  ✅ Suggestions when no matches found