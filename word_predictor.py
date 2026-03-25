"""
<<<<<<< HEAD
Word Predictor - Next-Word Prediction Engine

This module provides intelligent word prediction based on typing history
and a pre-built word frequency dictionary.
=======
word_predictor.py
-----------------
N-gram + frequency-based next-word prediction engine.
Supports prefix matching, user history learning, and sentence-aware suggestions.
>>>>>>> 52c3d7ea5ed405484f229b508704a40d14764e6c
"""

import json
import os
import re
from collections import defaultdict, Counter
<<<<<<< HEAD
import heapq

# Configuration constants
CONFIG = {
    'max_suggestions': 4,
    'history_file': 'word_history.json',
    'frequency_file': 'word_frequencies.json',
    'min_word_length': 2,
    'max_context_words': 3,
    'decay_factor': 0.9,  # For recency weighting
}

class WordPredictor:
    """
    Word prediction engine using n-gram models and frequency analysis.
    """

    def __init__(self):
        """Initialize word predictor."""
        self.word_frequencies = {}
        self.user_history = defaultdict(Counter)
        self.context_history = defaultdict(lambda: defaultdict(Counter))
        self.total_words = 0

        # Load pre-built word frequency dictionary
        self.load_word_frequencies()

        # Common English words for fallback
        self.common_words = [
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
            'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
            'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
            'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
            'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me',
            'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
            'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other',
            'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
            'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way',
            'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us'
        ]

    def load_word_frequencies(self):
        """Load pre-built word frequency dictionary."""
        try:
            if os.path.exists(CONFIG['frequency_file']):
                with open(CONFIG['frequency_file'], 'r') as f:
                    self.word_frequencies = json.load(f)
                print(f"Loaded {len(self.word_frequencies)} word frequencies")
            else:
                print("Word frequency file not found, using common words only")
                # Create basic frequency dict from common words
                for i, word in enumerate(self.common_words):
                    self.word_frequencies[word] = len(self.common_words) - i
        except Exception as e:
            print(f"Error loading word frequencies: {e}")

    def load_history(self, profile_name):
        """Load user typing history for a profile."""
        if not profile_name:
            return

        history_file = f"profiles/{profile_name}/{CONFIG['history_file']}"
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    self.user_history = defaultdict(Counter, data.get('user_history', {}))
                    self.context_history = defaultdict(lambda: defaultdict(Counter),
                                                     data.get('context_history', {}))
                print(f"Loaded history for profile {profile_name}")
        except Exception as e:
            print(f"Error loading history for {profile_name}: {e}")

    def save_history(self, profile_name):
        """Save user typing history for a profile."""
        if not profile_name:
            return

        os.makedirs(f"profiles/{profile_name}", exist_ok=True)
        history_file = f"profiles/{profile_name}/{CONFIG['history_file']}"

        try:
            data = {
                'user_history': dict(self.user_history),
                'context_history': dict(self.context_history)
            }
            with open(history_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Saved history for profile {profile_name}")
        except Exception as e:
            print(f"Error saving history for {profile_name}: {e}")

    def get_suggestions(self, current_text):
        """
        Get word suggestions based on current text.

        Args:
            current_text: Current text in the text area

        Returns:
            list: List of suggested words
        """
        if not current_text or not current_text.strip():
            return self.get_fallback_suggestions()

        # Clean and tokenize text
        words = self.tokenize_text(current_text)

        if not words:
            return self.get_fallback_suggestions()

        # Get last few words for context
        context = words[-CONFIG['max_context_words']:]

        # Generate suggestions
        suggestions = []

        # Context-based suggestions
        context_suggestions = self.get_context_suggestions(context)
        suggestions.extend(context_suggestions)

        # Prefix-based suggestions
        last_word = words[-1].lower()
        if len(last_word) >= CONFIG['min_word_length']:
            prefix_suggestions = self.get_prefix_suggestions(last_word)
            suggestions.extend(prefix_suggestions)

        # Frequency-based suggestions
        freq_suggestions = self.get_frequency_suggestions()
        suggestions.extend(freq_suggestions)

        # Remove duplicates and limit
        seen = set()
        unique_suggestions = []
        for word in suggestions:
            if word not in seen and len(unique_suggestions) < CONFIG['max_suggestions']:
                seen.add(word)
                unique_suggestions.append(word)

        # If we don't have enough suggestions, add common words
        while len(unique_suggestions) < CONFIG['max_suggestions']:
            for common_word in self.common_words:
                if common_word not in seen:
                    unique_suggestions.append(common_word)
                    seen.add(common_word)
                    break

        return unique_suggestions[:CONFIG['max_suggestions']]

    def tokenize_text(self, text):
        """Tokenize text into words."""
        # Remove punctuation and split
        words = re.findall(r'\b\w+\b', text.lower())
        return [word for word in words if len(word) >= CONFIG['min_word_length']]

    def get_context_suggestions(self, context):
        """Get suggestions based on word context."""
        if not context:
            return []

        suggestions = []

        # Look for patterns in context history
        context_key = tuple(context)
        if context_key in self.context_history:
            next_words = self.context_history[context_key]

            # Get top suggestions by frequency
            top_words = heapq.nlargest(
                CONFIG['max_suggestions'] * 2,
                next_words.items(),
                key=lambda x: x[1]
            )

            suggestions.extend([word for word, count in top_words])

        return suggestions

    def get_prefix_suggestions(self, prefix):
        """Get suggestions based on word prefix."""
        suggestions = []

        # Check user history for words starting with prefix
        for word, count in self.user_history.items():
            if word.startswith(prefix) and word != prefix:
                suggestions.append((word, count))

        # Check word frequencies for words starting with prefix
        for word, freq in self.word_frequencies.items():
            if word.startswith(prefix) and word != prefix:
                suggestions.append((word, freq))

        # Sort by frequency/count and return words
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [word for word, count in suggestions[:CONFIG['max_suggestions']]]

    def get_frequency_suggestions(self):
        """Get suggestions based on overall word frequency."""
        # Get most common words from user history
        user_common = heapq.nlargest(
            CONFIG['max_suggestions'],
            self.user_history.items(),
            key=lambda x: x[1]
        )

        # Get most common words from frequency dict
        freq_common = heapq.nlargest(
            CONFIG['max_suggestions'],
            self.word_frequencies.items(),
            key=lambda x: x[1]
        )

        suggestions = []
        suggestions.extend([word for word, count in user_common])
        suggestions.extend([word for word, count in freq_common])

        return suggestions

    def get_fallback_suggestions(self):
        """Get fallback suggestions when no context is available."""
        return self.common_words[:CONFIG['max_suggestions']]

    def update_history(self, current_text, profile_name):
        """
        Update word prediction history with new text.

        Args:
            current_text: Current text content
            profile_name: User profile name
        """
        words = self.tokenize_text(current_text)

        if len(words) < 2:
            return

        # Update unigram frequencies
        for word in words:
            self.user_history[word] += 1
            self.total_words += 1

        # Update n-gram contexts
        for i in range(len(words) - 1):
            context = tuple(words[max(0, i - CONFIG['max_context_words'] + 1):i + 1])
            next_word = words[i + 1]

            if len(context) > 0:
                self.context_history[context][next_word] += 1

        # Save history periodically
        if profile_name and self.total_words % 100 == 0:  # Save every 100 words
            self.save_history(profile_name)

    def add_custom_word(self, word, profile_name):
        """Add a custom word to the user's vocabulary."""
        if profile_name and word:
            self.user_history[word.lower()] += 1
            self.save_history(profile_name)

    def clear_history(self, profile_name):
        """Clear user's typing history."""
        self.user_history.clear()
        self.context_history.clear()
        self.total_words = 0

        if profile_name:
            history_file = f"profiles/{profile_name}/{CONFIG['history_file']}"
            try:
                if os.path.exists(history_file):
                    os.remove(history_file)
                print(f"Cleared history for profile {profile_name}")
            except Exception as e:
                print(f"Error clearing history: {e}")

    def get_word_stats(self):
        """Get statistics about the word predictor."""
        return {
            'total_words': self.total_words,
            'unique_words': len(self.user_history),
            'context_patterns': len(self.context_history),
            'frequency_words': len(self.word_frequencies)
        }

    def export_word_list(self, filename):
        """Export user's word list to a file."""
        try:
            word_list = sorted(self.user_history.items(), key=lambda x: x[1], reverse=True)
            with open(filename, 'w') as f:
                f.write("Word,Frequency\n")
                for word, count in word_list:
                    f.write(f"{word},{count}\n")
            print(f"Exported word list to {filename}")
        except Exception as e:
            print(f"Error exporting word list: {e}")

# Create default word frequency file if it doesn't exist
def create_default_frequencies():
    """Create a default word frequency file."""
    if not os.path.exists(CONFIG['frequency_file']):
        # Use common words with decreasing frequencies
        frequencies = {}
        base_freq = 10000
        for i, word in enumerate([
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
            'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
            'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
            'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
            'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me',
            'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
            'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other',
            'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
            'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way',
            'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us'
        ]):
            frequencies[word] = base_freq - (i * 100)

        try:
            with open(CONFIG['frequency_file'], 'w') as f:
                json.dump(frequencies, f, indent=2)
            print(f"Created default word frequency file with {len(frequencies)} words")
        except Exception as e:
            print(f"Error creating frequency file: {e}")

# Initialize default frequencies on import
create_default_frequencies()
=======

# ── CONFIG ──────────────────────────────────────────────────────────────────
CONFIG = {
    "MAX_SUGGESTIONS": 4,
    "USER_WORDS_FILE": "user_words.json",
    "MAX_USER_HISTORY": 5000,       # max entries in user word history
    "MIN_PREFIX_LEN": 1,            # minimum prefix length to trigger prediction
}
# ────────────────────────────────────────────────────────────────────────────

# Top-500 English words (compact built-in list; extend via user_words.json)
BUILTIN_WORDS = """the be to of and a in that have it for not on with he as you do at
this but his by from they we say her she or an will my one all would there their what
so up out if about who get which go me when make can like time no just him know take
people into year your good some could them see other than then now look only come its
over think also back after use two how our work first well way even new want because
any these give day most us great between need large often hand high place hold today
world every found still learn plant cover food sun four between state keep eye never
last let thought city tree cross farm hard start might story saw far sea draw left
late run don't while press close night real life few north open seem together next
white children begin got walk example ease paper group always music those both mark
book letter until mile river car feet care second enough plain girl usual young ready
above ever red list though feel talk bird soon body dog family direct pose leave song
measure door product black short numeral class wind question happen complete ship area
half rock order fire south problem piece told knew pass since top whole king space
heard best hour better true during hundred five remember step early hold west ground
interest reach fast verb sing listen six table travel less morning ten simple several
vowel toward war lay against pattern slow center love person money serve appear road
map rain rule govern pull cold notice voice unit power town fine drive exist air
clean break lady river pretty print job edge sign visit past soft fun bright gas
weather month million bear finish happy hope flower clothe strange gone jump baby
eight village meet root buy raise solve metal whether push seven paragraph third
shall held hair describe cook floor either result burn hill safe cat century consider
type law bit coast copy phrase silent tall sand soil roll temperature finger industry
done boat art science captain planet direct control health ear else quite broke case
middle kill son lake moment scale loud spring observe child straight consonant nation
dictionary milk speed method organ pay age section dress cloud surprise quiet stone
tiny climb cool design poor lot experiment bottom key iron single stick flat twenty
skin smile crease hole jump baby eight village meet root buy raise solve metal
whether push seven paragraph third shall held hair describe cook floor either result
burn hill safe cat century consider type law bit coast copy phrase silent tall sand
soil roll temperature finger industry done boat art science captain planet direct
control health ear else quite broke case middle kill son lake moment scale loud
spring observe child straight consonant nation dictionary milk speed method organ pay
age section dress cloud surprise quiet stone tiny climb cool design poor lot
experiment bottom key iron single stick flat twenty skin smile crease hole trade
melody trip office receive row mouth exact symbol die least trouble shout except
wrote seed tone join suggest clean break lady river pretty print job edge sign visit
past soft fun bright gas weather month million bear finish happy hope flower clothe
strange gone jump baby eight village meet root buy raise solve metal whether push
seven paragraph third shall held hair describe cook floor either result burn hill
safe cat century consider type law bit coast copy phrase silent tall sand soil roll
temperature finger industry done boat art science captain planet direct control
health ear else quite broke case middle kill son lake moment scale loud spring
observe child straight consonant nation dictionary milk speed method organ pay age
section dress cloud surprise quiet stone tiny climb cool design poor lot experiment
bottom key iron single stick flat twenty skin smile crease hole trade melody trip
office receive row mouth exact symbol die least trouble shout except wrote seed tone
join suggest clean break lady river pretty print job edge sign visit past soft fun
bright gas weather month million bear finish happy hope flower clothe strange gone""".split()


class WordPredictor:
    """
    Predicts next words based on:
    1. Current prefix (what the user is typing)
    2. Previous word context (bigram model)
    3. User typing history (personalised frequency)
    """

    def __init__(self):
        # Word frequency table: word → count
        self.word_freq = Counter(BUILTIN_WORDS)

        # Bigram model: previous_word → Counter of next words
        self.bigrams = defaultdict(Counter)

        # User history
        self.user_words = Counter()
        self._load_user_words()

        # Build bigrams from built-in word list (sequential pairs)
        self._build_bigrams(BUILTIN_WORDS)

    # ── Public API ───────────────────────────────────────────────────────────

    def predict(self, current_text):
        """
        Given the full typed text so far, return up to MAX_SUGGESTIONS words.
        current_text: str – everything typed so far
        Returns: list of str
        """
        words = current_text.strip().split()
        if not words:
            # No text yet – return most common words
            return self._top_words(CONFIG["MAX_SUGGESTIONS"])

        last_word = words[-1]
        prev_word = words[-2].lower() if len(words) >= 2 else ""

        # If last character is a space, predict next word
        if current_text.endswith(" "):
            return self._predict_next(prev_word=last_word.lower())

        # Otherwise predict completions for current prefix
        prefix = last_word.lower()
        if len(prefix) < CONFIG["MIN_PREFIX_LEN"]:
            return self._predict_next(prev_word=prev_word)

        return self._predict_prefix(prefix, prev_word)

    def learn(self, word):
        """Record a word the user typed to improve future predictions."""
        w = word.strip().lower()
        if w and w.isalpha():
            self.user_words[w] += 1
            self.word_freq[w] += 1
            self._save_user_words()

    def learn_sentence(self, text):
        """Learn all words from a completed sentence."""
        words = re.findall(r"[a-zA-Z']+", text.lower())
        for w in words:
            self.learn(w)
        # Update bigrams
        self._build_bigrams(words)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _predict_prefix(self, prefix, prev_word=""):
        """Return words that start with prefix, ranked by frequency + context."""
        candidates = [w for w in self.word_freq if w.startswith(prefix)]
        return self._rank(candidates, prev_word)[: CONFIG["MAX_SUGGESTIONS"]]

    def _predict_next(self, prev_word=""):
        """Predict next word given previous word context."""
        if prev_word and prev_word in self.bigrams:
            bigram_candidates = list(self.bigrams[prev_word].keys())
            ranked = self._rank(bigram_candidates, prev_word)
            if len(ranked) >= CONFIG["MAX_SUGGESTIONS"]:
                return ranked[: CONFIG["MAX_SUGGESTIONS"]]
        return self._top_words(CONFIG["MAX_SUGGESTIONS"])

    def _rank(self, candidates, prev_word=""):
        """
        Score candidates by:
        - User history weight (3x)
        - Bigram context weight (2x)
        - Global frequency (1x)
        """
        def score(w):
            user_score = self.user_words.get(w, 0) * 3
            bigram_score = self.bigrams[prev_word].get(w, 0) * 2 if prev_word else 0
            freq_score = self.word_freq.get(w, 0)
            return user_score + bigram_score + freq_score

        return sorted(candidates, key=score, reverse=True)

    def _top_words(self, n):
        """Return top-n most frequent words overall."""
        combined = self.word_freq + self.user_words
        return [w for w, _ in combined.most_common(n)]

    def _build_bigrams(self, word_list):
        """Build bigram counts from a list of words."""
        for i in range(len(word_list) - 1):
            w1 = word_list[i].lower()
            w2 = word_list[i + 1].lower()
            if w1.isalpha() and w2.isalpha():
                self.bigrams[w1][w2] += 1

    def _load_user_words(self):
        path = CONFIG["USER_WORDS_FILE"]
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                self.user_words = Counter(data)
            except Exception as e:
                print(f"[WordPredictor] Could not load user words: {e}")

    def _save_user_words(self):
        path = CONFIG["USER_WORDS_FILE"]
        try:
            # Trim to max history size
            trimmed = dict(self.user_words.most_common(CONFIG["MAX_USER_HISTORY"]))
            with open(path, "w") as f:
                json.dump(trimmed, f)
        except Exception as e:
            print(f"[WordPredictor] Could not save user words: {e}")
>>>>>>> 52c3d7ea5ed405484f229b508704a40d14764e6c
