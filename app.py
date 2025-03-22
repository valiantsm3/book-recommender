from flask import Flask, render_template, request
import pickle
import pandas as pd
import difflib
import requests

app = Flask(__name__)

# Load preprocessed data
books = pickle.load(open("book-recommender/books.pkl", "rb"))
popular = pickle.load(open("book-recommender/popular.pkl", "rb"))
pt = pickle.load(open("book-recommender/pt.pkl", "rb"))
similarity_scores = pickle.load(open("book-recommender/similarity_scores.pkl", "rb"))

@app.route('/')
def index():
    # Convert popular books data to list of dictionaries for easier iteration in template
    data = popular[['Book-Title', 'Book-Author', 'Image-URL-M', 'num_ratings', 'avg_rating']] \
        .to_dict(orient='records')
    return render_template("index.html", books=data)

@app.route('/recommend')
def recommend_page():
    return render_template("recommend.html", user_input="")

@app.route('/recommend_books', methods=['POST'])
def recommend_books():
    user_input = request.form.get("book_name", "").strip().lower()
    if not user_input:
        return render_template("recommend.html", error="Please enter a book title.", user_input="")

    # Prepare matching with the pivot table index
    pt_index_lower = [str(title).strip().lower() for title in pt.index]
    matched_input = next((title for title in pt_index_lower if user_input in title), None) or \
                    next(iter(difflib.get_close_matches(user_input, pt_index_lower, n=1, cutoff=0.6)), None)
    if not matched_input:
        return render_template("recommend.html", error="Book not found. Please try another title.", user_input=user_input)

    index_loc = pt_index_lower.index(matched_input)
    similar_books = sorted(
        list(enumerate(similarity_scores[index_loc])),
        key=lambda x: x[1],
        reverse=True
    )[1:5]

    recommendations = []
    for idx, score in similar_books:
        recommended_title = pt.index[idx]
        matched_rows = books[books['Book-Title'].str.lower().str.strip() == recommended_title.lower().strip()]
        if not matched_rows.empty:
            details = matched_rows.iloc[0]
            rec_title = details['Book-Title']
            rec_author = details['Book-Author']
            rec_image = details['Image-URL-M']
        else:
            rec_title = recommended_title
            rec_author = "Unknown"
            rec_image = "https://via.placeholder.com/150"
        recommendations.append((rec_title, rec_author, rec_image))

    return render_template("recommend.html", recommendations=recommendations, user_input=user_input)

# New route: Clicking a book opens details page with summary (via Google Books API)
@app.route('/book/<string:book_title>')
def book_details(book_title):
    query = "intitle:" + book_title
    url = "https://www.googleapis.com/books/v1/volumes?q=" + query
    response = requests.get(url)
    data = response.json()
    
    if "items" in data:
        book_data = data["items"][0]["volumeInfo"]
        title = book_data.get("title", "No Title")
        authors = ", ".join(book_data.get("authors", []))
        description = book_data.get("description", "No description available.")
        preview_link = book_data.get("previewLink", "#")
    else:
        title = book_title
        authors = "Unknown"
        description = "No description available."
        preview_link = "#"
    
    return render_template("book_details.html",
                           title=title,
                           authors=authors,
                           description=description,
                           preview_link=preview_link)

if __name__ == "__main__":
    app.run(debug=True)
