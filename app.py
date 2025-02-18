import os
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
import pyfiglet

# 🔹 Chargement de la clé API
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

console = Console()
PREFS_FILE = "cleaner_prefs.json"

# 🔹 Chargement des préférences
def load_preferences():
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            console.print("[red]⚠️ Erreur dans le fichier de préférences, réinitialisation...[/red]")
            return {}
    return {}

def save_preferences(prefs):
    with open(PREFS_FILE, "w") as f:
        json.dump(prefs, f, indent=4)

# 🔹 Scan du stockage
def scan_storage(folder, size_limit=50, days_old=180):
    if not os.path.exists(folder):
        console.print(f"[red]❌ Le dossier {folder} n'existe pas.[/red]")
        return []

    files = []
    now = time.time()

    for root, _, filenames in os.walk(folder):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            try:
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path) / (1024 * 1024)  # Mo
                    age_days = (now - os.path.getatime(file_path)) / 86400  # Jours
                    if size > size_limit or age_days > days_old:
                        files.append((file_path, size, age_days))
            except Exception as e:
                console.print(f"[yellow]⚠️ Erreur avec {file_path}: {e}[/yellow]")
                continue

    return sorted(files, key=lambda x: x[1], reverse=True)

# 🔹 Nettoyage des caches
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
                        if os.access(file_path, os.W_OK):  # Vérifie l'accès en écriture
                            send2trash(file_path)
                            cleaned_files += 1
                    except Exception as e:
                        console.print(f"[yellow]⚠️ Impossible de supprimer {file_path}: {e}[/yellow]")

    return cleaned_files

# 🔹 Consultation GPT-4
def ask_gpt4(question):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": question}]
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        console.print(f"[red]⚠️ Erreur GPT-4: {e}[/red]")
        return "⚠️ Erreur de connexion à GPT-4."

# 🔹 Interface utilisateur
def main():
    console.print("\n🔍 [bold cyan]Scan du stockage en cours...[/bold cyan]")
    
    storage_path = "/sdcard" if os.path.exists("/sdcard") else "/storage/emulated/0"
    files = scan_storage(storage_path, size_limit=50, days_old=180)

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
            for path, _, _ in files[:5]:
                if os.path.exists(path):
                    try:
                        send2trash(path)
                        console.print(f"🗑️ [red]Supprimé : {path}[/red]")
                    except Exception as e:
                        console.print(f"⚠️ [yellow]Impossible de supprimer {path}: {e}[/yellow]")
        else:
            console.print("[green]❌ Suppression annulée.[/green]")

    elif response == "📅 Supprimer les fichiers les plus anciens":
        confirmation = Confirm.ask("[bold red]Confirmer la suppression des fichiers vieux de plus de 6 mois ?[/bold red]")
        if confirmation:
            for path, _, _ in files[:5]:
                if os.path.exists(path):
                    try:
                        send2trash(path)
                        console.print(f"🗑️ [red]Supprimé : {path}[/red]")
                    except Exception as e:
                        console.print(f"⚠️ [yellow]Impossible de supprimer {path}: {e}[/yellow]")
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
    title = pyfiglet.figlet_format("TrHackNon Cleaner", font="slant")
    console.print(f"[bold cyan]{title}[/bold cyan]")
    main()
