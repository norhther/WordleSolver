import math
from collections import Counter
from unidecode import unidecode


# Load word list
def load_word_list(file_path):
    with open(file_path, 'r') as file:
        return [unidecode(line.strip().lower()) for line in file if len(line.strip()) == 5]

# Generate feedback pattern for a guess-target pair
def get_feedback(guess, target):
    feedback = [0] * 5  # 0 = gray, 1 = yellow, 2 = green
    target_chars = list(target)

    # First pass: Find greens
    for i in range(5):
        if guess[i] == target_chars[i]:
            feedback[i] = 2
            target_chars[i] = None

    # Second pass: Find yellows
    for i in range(5):
        if feedback[i] == 0 and guess[i] in target_chars:
            feedback[i] = 1
            target_chars[target_chars.index(guess[i])] = None

    return tuple(feedback)

# Calculate entropy for a single guess
def calculate_entropy(guess, possible_words):
    feedback_counts = Counter(get_feedback(guess, word) for word in possible_words)
    total_words = len(possible_words)

    entropy = 0.0
    for count in feedback_counts.values():
        probability = count / total_words
        entropy -= probability * math.log2(probability)
    return entropy

# Find the top N guesses based on entropy
def find_top_guesses(word_list, top_n=10):
    entropy_scores = []

    for guess in word_list:
        entropy = calculate_entropy(guess, word_list)
        entropy_scores.append((guess, entropy))

    # Sort by entropy in descending order
    entropy_scores.sort(key=lambda x: x[1], reverse=True)
    return entropy_scores[:top_n]

if __name__ == "__main__":
    # Load word list
    word_list = load_word_list("wordlist.txt")

    # Find the top 10 guesses
    top_guesses = find_top_guesses(word_list, top_n=10)

    # Display the results
    print("Top 10 guesses based on entropy:")
    for rank, (word, entropy) in enumerate(top_guesses, start=1):
        print(f"{rank}. {word} (Entropy: {entropy:.4f})")
