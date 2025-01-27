import math
from collections import defaultdict, Counter
import sys
import multiprocessing
import os
import pickle
import hashlib
from unidecode import unidecode

ENTROPY_CACHE_FILE = "initial_entropy.pkl"
WORDLIST_HASH_FILE = "wordlist_hash.txt"

def load_word_list(file_path):
    """
    Load a list of valid 5-letter words from the specified file.

    Args:
        file_path (str): Path to the word list file.

    Returns:
        list: A list of valid 5-letter words in lowercase.
    """
    try:
        with open(file_path, 'r') as file:
            words = [unidecode(line.strip().lower()) for line in file if len(line.strip()) == 5]
        if not words:
            print("The word list is empty. Please ensure 'wordlist.txt' contains valid 5-letter words.")
            sys.exit(1)
        return words
    except FileNotFoundError:
        print(f"File '{file_path}' not found. Please ensure it exists in the current directory.")
        sys.exit(1)

feedback_cache = {}

def get_feedback(guess, target):
    """
    Simulate the feedback for a given guess against the target word.

    Args:
        guess (str): The guessed word.
        target (str): The target word.

    Returns:
        int: An integer representing the feedback pattern.
             Each position uses 2 bits:
             00 - gray
             01 - yellow
             10 - green
             Example: 'g y b b g' -> 10 01 00 00 10 (binary) -> 578 (decimal)
    """
    key = (guess, target)
    if key in feedback_cache:
        return feedback_cache[key]

    feedback = 0
    target_chars = list(target)

    # First pass: Identify greens
    for i in range(5):
        if guess[i] == target_chars[i]:
            feedback |= (2 << (2 * (4 - i)))  # Set bits to '10' for green
            target_chars[i] = None  # Remove matched character

    # Second pass: Identify yellows
    for i in range(5):
        if (feedback & (3 << (2 * (4 - i)))) >> (2 * (4 - i)) == 0:  # If not green
            if guess[i] in target_chars:
                feedback |= (1 << (2 * (4 - i)))  # Set bits to '01' for yellow
                target_chars[target_chars.index(guess[i])] = None  # Remove to prevent duplicate matches

    feedback_cache[key] = feedback
    return feedback

def group_feedback_patterns(guess, possible_words):
    """
    Group possible words based on the feedback patterns they produce for a given guess.

    Args:
        guess (str): The current guess word.
        possible_words (list): List of possible target words.

    Returns:
        defaultdict: A dictionary mapping feedback patterns to lists of words.
    """
    pattern_groups = defaultdict(list)
    for word in possible_words:
        pattern = get_feedback(guess, word)
        pattern_groups[pattern].append(word)
    return pattern_groups

def calculate_entropy(guess, possible_words):
    """
    Calculate the entropy of a guess based on the distribution of feedback patterns.

    Args:
        guess (str): The guessed word.
        possible_words (list): List of possible target words.

    Returns:
        float: The entropy value in bits.
    """
    pattern_counts = Counter()
    for word in possible_words:
        pattern = get_feedback(guess, word)
        pattern_counts[pattern] += 1

    total = len(possible_words)
    entropy = 0.0
    for count in pattern_counts.values():
        probability = count / total
        entropy -= probability * math.log2(probability)
    return entropy

def calculate_entropy_wrapper(args):
    """
    Wrapper function for multiprocessing to calculate entropy.

    Args:
        args (tuple): A tuple containing (guess, possible_words).

    Returns:
        tuple: A tuple containing (guess, entropy).
    """
    guess, possible_words = args
    entropy = calculate_entropy(guess, possible_words)
    return (guess, entropy)

def select_best_guess_parallel(word_list, possible_words):
    """
    Select the best guess word that maximizes entropy using parallel processing.

    Args:
        word_list (list): The full list of valid guess words.
        possible_words (list): Current list of possible target words.

    Returns:
        str: The selected best guess word.
    """
    num_processes = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(processes=num_processes)

    try:
        # Prepare arguments for each guess
        args = [(guess, possible_words) for guess in possible_words]
        # Calculate entropy in parallel
        results = pool.map(calculate_entropy_wrapper, args, chunksize=1000)
    finally:
        pool.close()
        pool.join()

    best_guess, max_entropy = max(results, key=lambda x: x[1])
    return best_guess


def filter_possible_words(guess, feedback, possible_words):
    """
    Filter the list of possible words based on the feedback received from a guess.

    Args:
        guess (str): The guessed word.
        feedback (int): Integer representing feedback pattern.
        possible_words (list): Current list of possible target words.

    Returns:
        list: Updated list of possible target words.
    """
    filtered_words = []
    for word in possible_words:
        if get_feedback(guess, word) == feedback:
            filtered_words.append(word)
    return filtered_words


def parse_feedback(feedback_str):
    """
    Convert a feedback string into a standardized integer format.

    Args:
        feedback_str (str): Feedback input string (e.g., 'g y b b g').

    Returns:
        int: An integer representing feedback pattern.

    Raises:
        ValueError: If the input format is incorrect.
    """
    feedback_map = {
        'g': 'green',
        'y': 'yellow',
        'b': 'gray',      # Using 'b' for gray
        'gray': 'gray',
        'green': 'green',
        'yellow': 'yellow'
    }
    feedback = []
    tokens = feedback_str.strip().lower().replace(',', ' ').split()
    for token in tokens:
        if token in feedback_map:
            feedback.append(feedback_map[token])
        else:
            raise ValueError(f"Invalid feedback token: '{token}'. Use 'g' for green, 'y' for yellow, 'b' or 'gray' for gray.")
    if len(feedback) != 5:
        raise ValueError("Feedback must consist of exactly 5 tokens.")
    
    # Convert feedback list to integer pattern
    feedback_int = 0
    for i in range(5):
        if feedback[i] == 'green':
            feedback_int |= (2 << (2 * (4 - i)))  # '10' for green
        elif feedback[i] == 'yellow':
            feedback_int |= (1 << (2 * (4 - i)))  # '01' for yellow
        # 'gray' remains '00', no action needed
    return feedback_int

def compute_wordlist_hash(word_list):
    """
    Compute a SHA256 hash of the word list to detect changes.

    Args:
        word_list (list): List of words.

    Returns:
        str: Hexadecimal SHA256 hash string.
    """
    hasher = hashlib.sha256()
    for word in word_list:
        hasher.update(word.encode('utf-8'))
    return hasher.hexdigest()

def save_wordlist_hash(wordlist_hash):
    """
    Save the word list hash to a file.

    Args:
        wordlist_hash (str): Hexadecimal SHA256 hash string.
    """
    with open(WORDLIST_HASH_FILE, 'w') as file:
        file.write(wordlist_hash)

def load_wordlist_hash():
    """
    Load the word list hash from a file.

    Returns:
        str: Hexadecimal SHA256 hash string or None if file doesn't exist.
    """
    if not os.path.exists(WORDLIST_HASH_FILE):
        return None
    with open(WORDLIST_HASH_FILE, 'r') as file:
        return file.read().strip()

def is_entropy_cache_valid(word_list):
    """
    Check if the entropy cache exists and matches the current word list.

    Args:
        word_list (list): Current list of words.

    Returns:
        bool: True if cache is valid, False otherwise.
    """
    cached_hash = load_wordlist_hash()
    current_hash = compute_wordlist_hash(word_list)
    if cached_hash == current_hash and os.path.exists(ENTROPY_CACHE_FILE):
        return True
    return False

def compute_and_save_initial_entropy(word_list):
    """
    Compute entropy for all initial guesses and save to cache.

    Args:
        word_list (list): Full list of valid guess words.

    Returns:
        dict: Dictionary mapping guess words to their entropy values.
    """
    print("🕒 Computing initial entropy values. This may take a few minutes...")
    entropy_dict = {}
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    try:
        args = [(guess, word_list) for guess in word_list]
        results = pool.map(calculate_entropy_wrapper, args, chunksize=1000)
        for guess, entropy in results:
            entropy_dict[guess] = entropy
    finally:
        pool.close()
        pool.join()
    
    with open(ENTROPY_CACHE_FILE, 'wb') as file:
        pickle.dump(entropy_dict, file)
    
    wordlist_hash = compute_wordlist_hash(word_list)
    save_wordlist_hash(wordlist_hash)
    
    print("✅ Initial entropy values computed and saved.")
    return entropy_dict

def load_initial_entropy():
    """
    Load the initial entropy dictionary from the cache file.

    Returns:
        dict: Dictionary mapping guess words to their entropy values.
    """
    with open(ENTROPY_CACHE_FILE, 'rb') as file:
        entropy_dict = pickle.load(file)
    return entropy_dict

def get_initial_entropy(word_list):
    """
    Retrieve the initial entropy dictionary, computing and caching if necessary.

    Args:
        word_list (list): Full list of valid guess words.

    Returns:
        dict: Dictionary mapping guess words to their entropy values.
    """
    if is_entropy_cache_valid(word_list):
        print("📂 Loading precomputed initial entropy values from cache...")
        entropy_dict = load_initial_entropy()
    else:
        entropy_dict = compute_and_save_initial_entropy(word_list)
    return entropy_dict

def wordle_bot():
    """
    Main function to run the AI-driven Wordle bot.
    """
    word_list = load_word_list("wordlist.txt")
    possible_words = word_list.copy()

    initial_entropy = get_initial_entropy(word_list)

    attempts = 6

    print("🎮 Welcome to the Optimized AI Wordle Solver!")
    print("After each guess, please provide feedback using:")
    print("  'g' for green (correct letter and position)")
    print("  'y' for yellow (correct letter, wrong position)")
    print("  'b' for gray (incorrect letter)")
    print("Separate each feedback token with a space or comma.")
    print("Example input: g y b b g")
    print("-" * 50)

    for attempt in range(attempts):
        if not possible_words:
            print("🚫 No possible words remaining. Please check the feedback for any errors.")
            return

        if attempt == 0:
            guess = max(initial_entropy, key=initial_entropy.get)
            print(f"\n🔍 Attempt {attempt + 1}: {guess}")
        else:
            guess = select_best_guess_parallel(word_list, possible_words)
            print(f"\n🔍 Attempt {attempt + 1}: {guess}")

        while True:
            feedback_input = input("💬 Enter feedback (e.g., g y b b g): ").strip().lower()
            try:
                feedback = parse_feedback(feedback_input)
                break
            except ValueError as ve:
                print(f"⚠️ Error: {ve}")
                print("Please enter feedback again.")

        # Check if the guess is correct (all green)
        # All bits set to '10' for green: 2 << 8 | 2 << 6 | 2 << 4 | 2 << 2 | 2 = 2*256 + 2*64 + 2*16 + 2*4 + 2 = 512 + 128 + 32 + 8 + 2 = 682
        if feedback == 682:
            print("🎉 Congratulations! Wordle solved!")
            return

        # Filter the possible words based on feedback
        possible_words = filter_possible_words(guess, feedback, possible_words)
        print(f"📉 Remaining possible words: {len(possible_words)}")

    print("\n❌ Failed to solve Wordle within the allowed attempts.")


if __name__ == "__main__":
    if sys.platform.startswith('win'):
        multiprocessing.freeze_support()
    wordle_bot()
