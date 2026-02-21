import os
import json
import queue
import shutil
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import requests
from faster_whisper import WhisperModel


class WhisperTranslatorApp:
    """Tkinter application for audio/video transcription and translation."""

    LANG_CODES = {
        "Anglais": "en",
        "Francais": "fr",
        "Espagnol": "es",
        "Allemand": "de",
        "Italien": "it",
        "Japonais": "ja",
        "Chinois": "zh",
    }

    AUDIO_CODES = {
        "Anglais": "en",
        "Francais": "fr",
        "Espagnol": "es",
        "Allemand": "de",
        "Italien": "it",
        "Japonais": "ja",
        "Chinois": "zh",
    }

    SUPPORTED_EXTENSIONS = (".mp4", ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm")

    WHISPER_MODELS = ["tiny", "base", "small", "medium", "large", "large-v2"]

    OLLAMA_URL = "http://localhost:11434/api/generate"
    OLLAMA_MODEL = "mistral"

    # Dark theme colors
    BG_DARK = "#1e1e1e"
    BG_WIDGET = "#2d2d2d"
    BG_BUTTON = "#3c3c3c"
    FG_WHITE = "#ffffff"
    FG_LIGHT = "#eeeeee"
    FG_MUTED = "#cccccc"
    ACCENT_BLUE = "#0e639c"
    ACCENT_TEAL = "#007acc"
    ACCENT_PURPLE = "#8a2be2"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Whisper Translator - Traduction multilingue")
        self.root.geometry("900x800")
        self.root.configure(bg=self.BG_DARK)

        self._msg_queue = queue.Queue()

        self.dossier_var = tk.StringVar()
        self.model_var = tk.StringVar(value="medium")
        self.language_var = tk.StringVar(value="Francais")
        self.audio_lang_var = tk.StringVar(value="Anglais")
        self.progress_var = tk.DoubleVar()

        style = ttk.Style()
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor=self.BG_WIDGET,
                         background=self.ACCENT_TEAL, thickness=20)

        self._build_ui()
        self._poll_queue()

    # ──────────────────────────── UI ───────────────────────────────

    def _build_ui(self):
        tk.Label(self.root, text="Dossier contenant vos fichiers audio/video :",
                 font=("Segoe UI", 12), bg=self.BG_DARK,
                 fg=self.FG_WHITE).pack(pady=10)
        tk.Entry(self.root, textvariable=self.dossier_var, width=100,
                 bg=self.BG_WIDGET, fg=self.FG_WHITE,
                 insertbackground=self.FG_WHITE, relief="flat").pack(padx=10)
        tk.Button(self.root, text="Parcourir...", command=self._choose_directory,
                  bg=self.BG_BUTTON, fg=self.FG_WHITE, relief="flat").pack(pady=5)

        frame_choix = tk.Frame(self.root, bg=self.BG_DARK)
        frame_choix.pack(pady=5)

        labels = ["Modele :", "Langue cible :", "Langue de l'audio :"]
        combos = [
            (self.model_var, self.WHISPER_MODELS),
            (self.language_var, list(self.LANG_CODES.keys())),
            (self.audio_lang_var, list(self.AUDIO_CODES.keys())),
        ]
        for i, (label, (var, vals)) in enumerate(zip(labels, combos)):
            tk.Label(frame_choix, text=label, bg=self.BG_DARK,
                     fg="white").grid(row=0, column=i * 2, padx=5)
            ttk.Combobox(frame_choix, textvariable=var, values=vals,
                         width=15).grid(row=0, column=i * 2 + 1, padx=5)

        tk.Button(self.root, text="Lancer la traduction batch",
                  command=self._on_batch_transcribe, bg=self.ACCENT_BLUE,
                  fg="white", relief="flat").pack(pady=10)
        tk.Button(self.root, text="Tester un fichier",
                  command=self._on_test_single_file, bg=self.ACCENT_BLUE,
                  fg="white", relief="flat").pack(pady=5)
        tk.Button(self.root, text="Traduire les SRT avec Ollama",
                  command=self._on_ollama_srt, bg=self.ACCENT_PURPLE,
                  fg="white", relief="flat").pack(pady=5)
        tk.Button(self.root, text="Traduire un texte brut avec Ollama",
                  command=self._on_ollama_text, bg=self.ACCENT_TEAL,
                  fg="white", relief="flat").pack(pady=5)

        self.progress_label = tk.Label(self.root, text="Progression : 0%",
                                        font=("Segoe UI", 10),
                                        bg=self.BG_DARK, fg=self.FG_MUTED)
        self.progress_label.pack(pady=(5, 0))
        self.progressbar = ttk.Progressbar(self.root, variable=self.progress_var,
                                            maximum=100, length=600,
                                            style="TProgressbar")
        self.progressbar.pack(pady=(0, 10))

        self.log = tk.Text(self.root, height=25, width=110,
                            bg=self.BG_DARK, fg=self.FG_LIGHT,
                            insertbackground="white", wrap="word", relief="flat")
        self.log.pack(padx=10, pady=10)

    # ──────────────────── Thread-safe GUI updates ─────────────

    def _poll_queue(self):
        try:
            while True:
                action = self._msg_queue.get_nowait()
                action()
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _log_message(self, message, color=None):
        def _do():
            self.log.insert(tk.END, message + "\n")
            if color:
                self.log.tag_add(color, "end-2l", "end-1l")
                self.log.tag_config(color, foreground=color)
            self.log.see(tk.END)
        self._msg_queue.put(_do)
        print(message)

    def _update_progress(self, current, total):
        pct = int((current / total) * 100)
        def _do():
            self.progress_var.set(pct)
            self.progress_label.config(
                text=f"Fichier {current} sur {total} ({pct}%)")
        self._msg_queue.put(_do)

    def _clear_log(self):
        self._msg_queue.put(lambda: self.log.delete("1.0", tk.END))

    def _reset_progress(self):
        def _do():
            self.progress_var.set(0)
            self.progress_label.config(text="Progression : 0%")
        self._msg_queue.put(_do)

    def _show_info(self, title, message):
        self._msg_queue.put(lambda: messagebox.showinfo(title, message))

    # ──────────────────── Utilities ──────────────────────────

    @staticmethod
    def _check_ffmpeg():
        if shutil.which("ffmpeg") is None:
            messagebox.showerror(
                "FFmpeg manquant",
                "FFmpeg n'est pas detecte dans le PATH.\n"
                "Installez FFmpeg et assurez-vous qu'il est dans le PATH systeme.")
            return False
        return True

    @staticmethod
    def _format_timestamp(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    def _find_media_files(self, root_dir):
        results = []
        for dirpath, _, filenames in os.walk(root_dir):
            for fname in filenames:
                if fname.lower().endswith(self.SUPPORTED_EXTENSIONS):
                    results.append((os.path.join(dirpath, fname), dirpath, fname))
        return results

    def _call_ollama(self, text, source_lang="en", target_lang="fr"):
        target_names = {v: k for k, v in self.LANG_CODES.items()}
        target_name = target_names.get(target_lang, target_lang)

        prompt = (
            f"Traduis en {target_name} ce texte de sous-titre "
            f"sans modifier le style ni le decoupage :\n\n\"{text}\""
        )
        payload = {
            "model": self.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }
        try:
            response = requests.post(self.OLLAMA_URL, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data.get("response", text).strip()
        except requests.RequestException as e:
            self._log_message(f"Erreur Ollama : {e}", color="orange")
            return text

    # ──────────────────── Whisper transcription ────────────────

    def _transcribe_to_srt(self, model, file_path, output_path, audio_code,
                            target_code):
        task = "translate" if audio_code != target_code else "transcribe"
        segments, _info = model.transcribe(
            file_path,
            task=task,
            language=audio_code,
            **({"initial_prompt": "Traduis tout en francais."}
               if target_code == "fr" and task == "translate" else {}),
        )
        with open(output_path, "w", encoding="utf-8") as f:
            for idx, segment in enumerate(segments, start=1):
                start = self._format_timestamp(segment.start)
                end = self._format_timestamp(segment.end)
                text = segment.text.strip()
                f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")

    # ──────────────────── Button handlers ──────────────────────

    def _choose_directory(self):
        d = filedialog.askdirectory()
        if d:
            self.dossier_var.set(d)

    def _on_batch_transcribe(self):
        dossier = self.dossier_var.get()
        if not dossier or not os.path.isdir(dossier):
            messagebox.showerror("Erreur",
                                 "Veuillez selectionner un dossier valide.")
            return
        if not self._check_ffmpeg():
            return
        threading.Thread(target=self._batch_transcribe, args=(dossier,),
                         daemon=True).start()

    def _on_test_single_file(self):
        filetypes = [
            ("Fichiers audio/video",
             "*.mp4 *.mp3 *.wav *.m4a *.flac *.ogg *.webm"),
            ("Tous les fichiers", "*.*"),
        ]
        fichier = filedialog.askopenfilename(filetypes=filetypes)
        if not fichier:
            return
        if not self._check_ffmpeg():
            return
        threading.Thread(target=self._test_single_file, args=(fichier,),
                         daemon=True).start()

    def _on_ollama_srt(self):
        dossier = self.dossier_var.get()
        if not dossier or not os.path.isdir(dossier):
            messagebox.showerror("Erreur",
                                 "Veuillez selectionner un dossier valide.")
            return
        threading.Thread(target=self._translate_srt_ollama, args=(dossier,),
                         daemon=True).start()

    def _on_ollama_text(self):
        fichier = filedialog.askopenfilename(
            filetypes=[("Fichiers texte", "*.txt")])
        if not fichier:
            return
        threading.Thread(target=self._translate_text_ollama, args=(fichier,),
                         daemon=True).start()

    # ──────────────────── Worker threads ───────────────────────

    def _batch_transcribe(self, dossier):
        try:
            self._clear_log()
            self._reset_progress()

            selected_model = self.model_var.get()
            target_code = self.LANG_CODES.get(self.language_var.get(), "fr")
            audio_code = self.AUDIO_CODES.get(self.audio_lang_var.get(), "en")

            self._log_message(f"Dossier selectionne : {dossier}")
            self._log_message("Recherche des fichiers audio/video...\n")

            model = WhisperModel(selected_model, device="cpu",
                                  compute_type="int8")
            media_files = self._find_media_files(dossier)
            total = len(media_files)

            if total == 0:
                self._log_message("Aucun fichier audio/video trouve.",
                                  color="red")
                return

            nb_ok = 0
            nb_errors = 0

            for index, (filepath, parent, filename) in enumerate(media_files,
                                                                  start=1):
                self._update_progress(index, total)
                name_no_ext = os.path.splitext(filename)[0]
                output_dir = os.path.join(parent, f"subtitle_{target_code}")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, name_no_ext + ".srt")

                self._log_message("-" * 60)
                self._log_message(
                    f"Traitement : {filename} ({index}/{total})")

                try:
                    self._transcribe_to_srt(model, filepath, output_path,
                                             audio_code, target_code)
                    self._log_message(f"SRT sauvegarde : {output_path}",
                                      color="green")
                    nb_ok += 1
                except Exception as e:
                    nb_errors += 1
                    self._log_message(f"Erreur pour {filename} : {e}",
                                      color="red")
                    traceback.print_exc()

            self._log_message(
                f"\nTermine. {nb_ok} reussites, {nb_errors} echecs "
                f"sur {total}.", color="cyan")

            log_content_q = queue.Queue()
            self._msg_queue.put(
                lambda: log_content_q.put(self.log.get("1.0", tk.END)))
            log_text = log_content_q.get(timeout=5)
            log_path = os.path.join(
                dossier, f"whisper_traduction_log_{target_code}.txt")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(log_text)

            self._log_message(f"Log sauvegarde : {log_path}", color="cyan")
            self._show_info("Termine",
                            "Tous les fichiers ont ete traites.")

        except Exception as e:
            self._log_message(f"Erreur generale : {e}", color="red")
            traceback.print_exc()

    def _test_single_file(self, filepath):
        try:
            selected_model = self.model_var.get()
            target_code = self.LANG_CODES.get(self.language_var.get(), "fr")
            audio_code = self.AUDIO_CODES.get(self.audio_lang_var.get(), "en")

            self._log_message(f"Test de : {filepath}")

            model = WhisperModel(selected_model, device="cpu",
                                  compute_type="int8")
            task = "translate" if audio_code != target_code else "transcribe"

            segments, _info = model.transcribe(
                filepath, task=task, language=audio_code,
                **({"initial_prompt": "Traduis tout en francais."}
                   if target_code == "fr" and task == "translate" else {}),
            )

            self._log_message("\n--- Apercu du resultat ---", color="cyan")
            for i, segment in enumerate(segments):
                if i >= 10:
                    break
                start = self._format_timestamp(segment.start)
                end = self._format_timestamp(segment.end)
                self._log_message(
                    f"[{start} --> {end}] {segment.text.strip()}")
            self._log_message("--- Fin de l'apercu ---\n", color="cyan")

        except Exception as e:
            self._log_message(f"Erreur pendant le test : {e}", color="red")
            traceback.print_exc()

    def _translate_srt_ollama(self, dossier):
        source_code = self.AUDIO_CODES.get(self.audio_lang_var.get(), "en")
        target_code = self.LANG_CODES.get(self.language_var.get(), "fr")
        source_dir = os.path.join(dossier, f"subtitle_{source_code}")
        output_dir = os.path.join(dossier, f"subtitle_{target_code}")
        os.makedirs(output_dir, exist_ok=True)

        if not os.path.isdir(source_dir):
            self._log_message(
                f"Dossier source introuvable : {source_dir}", color="red")
            return

        srt_files = [f for f in os.listdir(source_dir) if f.endswith(".srt")]
        if not srt_files:
            self._log_message(
                f"Aucun fichier .srt dans {source_dir}", color="red")
            return

        for i, srt_name in enumerate(srt_files, start=1):
            input_path = os.path.join(source_dir, srt_name)
            output_path = os.path.join(output_dir, srt_name)
            self._log_message(
                f"Traduction Ollama : {srt_name} ({i}/{len(srt_files)})")

            try:
                lines = open(input_path, encoding="utf-8").read().splitlines()
                with open(output_path, "w", encoding="utf-8") as f_out:
                    bloc = []
                    for line in lines:
                        if line.strip() == "":
                            if len(bloc) >= 3:
                                numero = bloc[0]
                                timestamp = bloc[1]
                                texte = " ".join(bloc[2:])
                                translated = self._call_ollama(
                                    texte, source_code, target_code)
                                f_out.write(
                                    f"{numero}\n{timestamp}\n"
                                    f"{translated}\n\n")
                            bloc = []
                        else:
                            bloc.append(line)
                    if len(bloc) >= 3:
                        numero = bloc[0]
                        timestamp = bloc[1]
                        texte = " ".join(bloc[2:])
                        translated = self._call_ollama(
                            texte, source_code, target_code)
                        f_out.write(
                            f"{numero}\n{timestamp}\n{translated}\n\n")

                self._log_message(
                    f"Fichier traduit : {output_path}", color="green")
            except Exception as e:
                self._log_message(
                    f"Erreur traduction {srt_name} : {e}", color="red")
                traceback.print_exc()

    def _translate_text_ollama(self, filepath):
        target_code = self.LANG_CODES.get(self.language_var.get(), "fr")
        source_code = self.AUDIO_CODES.get(self.audio_lang_var.get(), "en")

        self._log_message(f"Traduction du fichier : {filepath}")
        try:
            text = open(filepath, encoding="utf-8").read()
            translated = self._call_ollama(text, source_code, target_code)

            output_path = (os.path.splitext(filepath)[0]
                           + f"_{target_code}.txt")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(translated)

            self._log_message(
                f"Traduction sauvegardee : {output_path}", color="green")
        except Exception as e:
            self._log_message(f"Erreur : {e}", color="red")
            traceback.print_exc()

    # ──────────────────── Entry point ──────────────────────────

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = WhisperTranslatorApp()
    app.run()
