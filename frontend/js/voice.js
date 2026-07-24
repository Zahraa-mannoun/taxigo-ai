/**
 * Voice input (Web Speech API SpeechRecognition) and text-to-speech
 * (SpeechSynthesis), with language fallback chains for Arabic since
 * voice/locale availability is inconsistent across browsers/OSes.
 */
(function (global) {
  "use strict";

  const LANG_CHAINS = {
    en: ["en-US", "en-GB", "en"],
    ar: ["ar-SA", "ar-EG", "ar-AE", "ar"],
    fr: ["fr-FR", "fr"],
  };

  const SpeechRecognitionImpl = global.SpeechRecognition || global.webkitSpeechRecognition;

  let recognition = null;
  let listening = false;
  let voicesCache = null;

  function isRecognitionSupported() {
    return !!SpeechRecognitionImpl;
  }

  function isSynthesisSupported() {
    return "speechSynthesis" in global;
  }

  function getVoices() {
    if (!isSynthesisSupported()) return [];
    if (!voicesCache || voicesCache.length === 0) {
      voicesCache = global.speechSynthesis.getVoices();
    }
    return voicesCache;
  }

  if (isSynthesisSupported()) {
    global.speechSynthesis.onvoiceschanged = () => {
      voicesCache = global.speechSynthesis.getVoices();
    };
  }

  function pickVoice(lang) {
    const chain = LANG_CHAINS[lang] || [lang];
    const voices = getVoices();
    for (const code of chain) {
      const match = voices.find((v) => v.lang && v.lang.toLowerCase() === code.toLowerCase());
      if (match) return match;
    }
    for (const code of chain) {
      const prefix = code.split("-")[0].toLowerCase();
      const match = voices.find((v) => v.lang && v.lang.toLowerCase().startsWith(prefix));
      if (match) return match;
    }
    return null;
  }

  /**
   * Start one-shot voice recognition.
   * @param {string} lang - "en" | "ar" | "fr"
   * @param {(transcript: string) => void} onResult
   * @param {(error: string) => void} onError
   * @param {() => void} onEnd
   */
  function startListening(lang, onResult, onError, onEnd) {
    if (!isRecognitionSupported()) {
      onError("not_supported");
      return;
    }
    if (listening) {
      stopListening();
    }

    recognition = new SpeechRecognitionImpl();
    recognition.lang = (LANG_CHAINS[lang] || [lang])[0];
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      onResult(transcript);
    };

    recognition.onerror = (event) => {
      if (event.error === "not-allowed" || event.error === "permission-denied") {
        onError("permission_denied");
      } else {
        onError(event.error || "unknown");
      }
    };

    recognition.onend = () => {
      listening = false;
      if (onEnd) onEnd();
    };

    try {
      recognition.start();
      listening = true;
    } catch (err) {
      onError("start_failed");
    }
  }

  function stopListening() {
    if (recognition && listening) {
      recognition.stop();
    }
    listening = false;
  }

  function isListening() {
    return listening;
  }

  /**
   * Speak text aloud in the given language, using the best available
   * voice from that language's fallback chain.
   */
  function speak(text, lang) {
    if (!isSynthesisSupported() || !text) return;
    global.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    const voice = pickVoice(lang);
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    } else {
      utterance.lang = (LANG_CHAINS[lang] || [lang])[0];
    }
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    global.speechSynthesis.speak(utterance);
  }

  global.TaxiGoVoice = {
    isRecognitionSupported,
    isSynthesisSupported,
    startListening,
    stopListening,
    isListening,
    speak,
  };
})(window);
