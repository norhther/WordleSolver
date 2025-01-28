# Wordle Solver Bot

A Wordle solver that efficiently guesses the correct word using entropy-based calculations. Optimized for large word lists (80,000+ words) with caching for fast initial guesses.

## Features

- **Entropy-based logic** for optimal word selection.
- **Precomputed entropy caching** to reduce startup time.
- **Parallel processing** for fast calculations.
- Automatically detects changes in the word list and updates cache.

## Requirements

- Python 3.7+
- Multiprocessing and hashlib (default in Python), and unidecode
- A valid `wordlist.txt` file with 5-letter words (one per line). We provide a spanish one in this repository.

## Usage

1. Clone this repository.
2. Ensure `wordlist.txt` is in the same directory.
3. Run the bot:

   ```bash
   python wordle.py
   ```

4. Follow the on-screen instructions to provide feedback after each guess.

## Example

```plaintext
🔍 Attempt 1: slate
💬 Enter feedback (e.g., g y b b g): b y b b g
📉 Remaining possible words: 1

🔍 Attempt 2: grape
💬 Enter feedback (e.g., g y b b g): g g g g g
🎉 Congratulations! Wordle solved!
```
