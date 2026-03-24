"""
word_predictor.py
-----------------
N-gram + frequency-based next-word prediction engine.
Supports prefix matching, user history learning, and sentence-aware suggestions.
"""

import json
import os
import re
from collections import defaultdict, Counter

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
