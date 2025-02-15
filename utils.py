import os
from models import db, ContentRecommendation
from transformers import pipeline

# Initialize the model
generator = pipeline('text-generation', model='gpt2')

def get_ai_response(message):
    try:
        # Generate response using GPT-2
        response = generator(
            message,
            max_length=150,
            num_return_sequences=1,
            temperature=0.7,
            pad_token_id=50256
        )
        # Extract the generated text
        generated_text = response[0]['generated_text']
        # Remove the input prompt from the response
        response_text = generated_text[len(message):].strip()
        return response_text if response_text else "I apologize, but I couldn't generate a meaningful response."
    except Exception as e:
        return f"I apologize, but I'm having trouble processing your request. Error: {str(e)}"

def generate_recommendations(user_id, topic, score):
    # Example recommendations based on topic and score
    recommendations = [
        {
            "title": f"Advanced {topic} Concepts",
            "description": f"Deep dive into advanced {topic} concepts",
            "type": "article",
            "url": f"https://example.com/{topic}"
        },
        {
            "title": f"{topic} Practice Exercises",
            "description": f"Interactive exercises to master {topic}",
            "type": "exercise",
            "url": f"https://example.com/{topic}/practice"
        }
    ]

    for rec in recommendations:
        recommendation = ContentRecommendation(
            user_id=user_id,
            title=rec['title'],
            description=rec['description'],
            type=rec['type'],
            url=rec['url']
        )
        db.session.add(recommendation)

    db.session.commit()
    return recommendations