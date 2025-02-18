import os
import shutil
import time
import json
import openai
import questionary
import psutil
from termcolor import colored
from send2trash import send2trash
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

# 🔹 Chargement de la clé API depuis .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

console = Console()

# 🔹 Configuration des fichiers de préférences
PREFS_FILE = "cleaner_prefs.json"

def load_preferences():
    if os.path.exists(PREFS_FILE):
        with open(PREFS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_preferences(prefs):
    with open(PREFS_FILE, "w") as f:
        json.dump(prefs, f)

# 🔹 Scan des fichiers volumineux et anciens
def scan_storage(folder, size_limit=50, days_old=180):
    files = []
    now = time.time()

    for root, _, filenames in os.walk(folder):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            try:
                size = os.path.getsize(file_path) / (1024 * 1024)  # Mo
                last_access = os.path.getatime(file_path)
                age_days = (now - last_access) / 86400  # Convertir en jours

                if size > size_limit or age_days > days_old:
                    files.append((file_path, size, age_days))
            except:
                continue

    return sorted(files, key=lambda x: x[1], reverse=True)

# 🔹 Nettoyage des caches et fichiers temporaires
def clean_caches():
    cache_dirs = [
        "/sdcard/Android/data/com.whatsapp/cache/",
        "/sdcard/Android/data/com.facebook.katana/cache/",
        "/sdcard/Download/",
        "/sdcard/DCIM/.thumbnails/",
        "/tmp/",
        "/var/tmp/"
    ]

    cleaned_files = 0
    for folder in cache_dirs:
        if os.path.exists(folder):
            for root, _, filenames in os.walk(folder):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    try:
                        os.remove(file_path)
                        cleaned_files += 1
                    except:
                        continue

    return cleaned_files

# 🔹 Consultation de GPT-4 pour suggestions
def ask_gpt4(question):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": question}]
        )
        return response["choices"][0]["message"]["content"]
    except:
        return "⚠️ Erreur de connexion à GPT-4."

# 🔹 Interface utilisateur
def main():
    console.print("\n🔍 [bold cyan]Scan du stockage en cours...[/bold cyan]")

    files = scan_storage("/sdcard", size_limit=50, days_old=180)

    if not files:
        console.print("[bold green]✅ Aucun fichier problématique trouvé.[/bold green]")
        return

    table = Table(title="📂 Fichiers trouvés", style="yellow")
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Fichier", style="white")
    table.add_column("Taille (Mo)", style="magenta")
    table.add_column("Âge (jours)", style="blue")

    for i, (path, size, age) in enumerate(files[:10], 1):
        table.add_row(str(i), os.path.basename(path), f"{size:.2f}", f"{age:.0f}")

    console.print(table)

    response = questionary.select(
        "Que voulez-vous faire ?",
        choices=[
            "🗑️ Supprimer les plus gros fichiers",
            "📅 Supprimer les fichiers les plus anciens",
            "🧹 Nettoyer le cache",
            "❌ Annuler"
        ]
    ).ask()

    if response == "🗑️ Supprimer les plus gros fichiers":
        confirmation = Confirm.ask("[bold red]Confirmer la suppression des fichiers volumineux ?[/bold red]")
        if confirmation:
            for path, _, _ in files[:5]:  # Supprimer les 5 plus gros fichiers
                try:
                    send2trash(path)
                    console.print(f"🗑️ [red]Supprimé : {path}[/red]")
                except:
                    console.print(f"⚠️ [yellow]Impossible de supprimer : {path}[/yellow]")
        else:
            console.print("[green]❌ Suppression annulée.[/green]")

    elif response == "📅 Supprimer les fichiers les plus anciens":
        confirmation = Confirm.ask("[bold red]Confirmer la suppression des fichiers vieux de plus de 6 mois ?[/bold red]")
        if confirmation:
            for path, _, _ in files[:5]:
                try:
                    send2trash(path)
                    console.print(f"🗑️ [red]Supprimé : {path}[/red]")
                except:
                    console.print(f"⚠️ [yellow]Impossible de supprimer : {path}[/yellow]")
        else:
            console.print("[green]❌ Suppression annulée.[/green]")

    elif response == "🧹 Nettoyer le cache":
        deleted = clean_caches()
        console.print(f"[green]✅ {deleted} fichiers de cache supprimés.[/green]")

    else:
        console.print("\n🤖 [yellow]Consultation de GPT-4 pour conseils...[/yellow]")
        suggestion = ask_gpt4("Je veux optimiser mon espace de stockage sur Android. Quels fichiers inutiles devrais-je supprimer ?")
        console.print(f"\n💡 [cyan]{suggestion}[/cyan]")

if __name__ == "__main__":
    os.system("figlet -f fontawesome-webfont 'TrHackNon Cleaner'")
    main()
