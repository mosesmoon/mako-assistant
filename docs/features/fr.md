# Assistant MAKO — Présentation des fonctionnalités

[English](en.md) · [台灣正體中文](zh_TW.md) · [简体中文](zh_CN.md) · [日本語](ja.md) · [Deutsch](de.md) · **Français** · [Español](es.md) · [Italiano](it.md) · [ไทย](th.md) · [Tiếng Việt](vi.md) · [Bahasa Melayu](ms.md) · [हिन्दी](hi.md)

L’**Assistant MAKO** est un outil graphique pour bureau Linux qui active ou désactive en un clic la **génération d’images de MAKO Renderer (Mako FG)** pour vos jeux Steam, sans modifier aucun fichier de configuration à la main.

## À qui s’adresse-t-il ?

Sur Steam Deck, en mode Jeu, MAKO dispose d’un plugin Decky qui permet de tout régler en jeu. Sur un **ordinateur de bureau ou portable Linux classique** (par exemple Arch, Fedora ou Ubuntu avec KDE Plasma ou GNOME), faire utiliser MAKO à un jeu demande en général de tout faire à la main :

1. Ajouter `~/.local/bin/mako-launch %command%` aux options de lancement Steam du jeu (Propriétés → Options de lancement) sans casser les options déjà présentes.
2. Trouver le nom du programme que le jeu **exécute réellement** (beaucoup de jeux démarrent d’abord un lanceur, et les jeux Unreal Engine exécutent un `*-Shipping.exe`).
3. Créer un profil de jeu dans les réglages de MAKO et y saisir les bons processus associés (`active_in`).
4. Tout recommencer quand une mise à jour du jeu change le chemin ou le nom de l’exécutable.
5. Lancer le jeu sans savoir avec certitude si la génération d’images fonctionne vraiment.

L’Assistant MAKO réunit ces étapes en un seul bouton et, pendant qu’un jeu tourne, indique quelles fonctions MAKO sont **réellement** actives.

## Avant de commencer

> ⚠ **L’Assistant MAKO n’inclut pas MAKO Renderer et ne l’installe pas pour vous.** Il se contente de gérer les réglages de MAKO.

Commencez par :

1. **Installer MAKO Renderer (version autonome)** en suivant les instructions d’installation de MAKO. Une fois l’installation terminée, `~/.local/bin/mako-launch` doit exister.
2. **Ouvrir MAKO UI une fois** pour créer les réglages par défaut. Cela crée `~/.config/mako-render/conf.toml` et le profil par défaut `mako`. Chaque profil de jeu créé par l’Assistant MAKO est une copie de ce profil par défaut.
3. **Installer Steam.** Le paquet natif (`~/.local/share/Steam`, `~/.steam`) ainsi que les versions Flatpak et Snap sont pris en charge.

Vérifiez que tout cela est fait et que MAKO lui-même fonctionne avant d’installer Mako FG pour un jeu avec l’Assistant MAKO.

Facultatif : **Decky Loader**. Avec lui, les options de lancement peuvent être appliquées en direct pendant que Steam tourne, sans fermer Steam (voir « Comment les options de lancement sont écrites » ci-dessous).

## Fonctionnalités

### 1. Analyse automatique de la bibliothèque Steam

- Au premier lancement, **toutes** vos bibliothèques Steam sont analysées (y compris celles situées sur d’autres disques). Ensuite, vous pouvez cliquer sur « ⟳ Réanalyser les jeux Steam ».
- Les outils comme Proton et le Steam Linux Runtime sont exclus : seuls les jeux sont listés.
- Les noms des jeux s’affichent sous leur nom localisé officiel Steam dans la langue de l’interface, et sont triés selon l’usage de cette langue.
- Chaque jeu affiche sa jaquette, ses options de lancement actuelles, son profil MAKO et les chemins de l’exécutable détectés.

### 2. « Installer Mako FG » en un clic

Quand vous cliquez sur « Installer Mako FG », l’outil :

- **Ajoute l’option de lancement** `~/.local/bin/mako-launch %command%` aux options de lancement Steam du jeu en **conservant ce qui s’y trouvait déjà**. Par exemple, `FOO=1 %command% -dx11` devient `FOO=1 ~/.local/bin/mako-launch %command% -dx11`.
- **Détecte le véritable exécutable du jeu** à partir des informations d’application de Steam. Il gère les lanceurs (il cherche alors le vrai programme du jeu dans le dossier d’installation) et les `*-Shipping.exe` d’Unreal Engine, et ignore les programmes auxiliaires courants.
- **Crée un profil de jeu MAKO** : il copie le profil par défaut `mako` dans un profil propre au jeu dans `conf.toml` et écrit les métadonnées de profil de MAKO. **MAKO UI et le plugin Decky voient tous deux ce profil et peuvent le modifier directement.**
- **Évite les doublons** : si le profil par défaut `mako` est aussi associé à l’exécutable de ce jeu, l’exécutable est retiré de `mako`, pour que le jeu n’utilise que son propre profil. Si le profil d’un autre jeu est associé au même exécutable, un avertissement s’affiche, mais rien n’est modifié automatiquement.

### 3. Comment les options de lancement sont écrites

Steam ne lit les options de lancement qu’à son démarrage et réécrit son fichier de configuration en quittant. Pour que Steam n’écrase pas votre modification, l’Assistant MAKO choisit la méthode d’écriture selon l’état de Steam et affiche cet état dans la fenêtre :

| État de Steam | Méthode d’écriture |
|---|---|
| Fermé | Modifie directement le `localconfig.vdf` de Steam (après une sauvegarde) |
| Ouvert, et le client Steam est joignable (nécessite Decky Loader) | Applique la modification en direct via le client Steam, sans redémarrer Steam |
| Ouvert, mais le client n’est pas joignable | Demande s’il faut fermer Steam → applique la modification → redémarre Steam |

### 4. Supprimer

- « Supprimer » retire seulement `mako-launch` des options de lancement et laisse vos autres options intactes.
- Les réglages MAKO du jeu sont **conservés par défaut**, pour être réutilisés si vous le réinstallez plus tard. Cochez « Supprimer aussi les réglages MAKO Renderer du jeu » pour les effacer également.

### 5. Importer des réglages existants

Si vous aviez déjà ajouté `mako-launch` à un jeu à la main, ce jeu affiche un bouton « Importer les réglages ». Un clic crée le profil MAKO du jeu et l’inclut désormais dans les mises à jour automatiques des chemins.

### 6. Mise à jour automatique des chemins après les mises à jour des jeux

- À chaque nouvelle analyse, l’outil détecte de nouveau les exécutables des jeux **installés avec cet outil**. Si une mise à jour a déplacé ou renommé l’exécutable, les processus associés de MAKO sont mis à jour automatiquement, et la modification est indiquée dans la zone de journal.
- Les processus associés que vous avez **ajoutés à la main** dans MAKO UI sont conservés.
- Si vous avez supprimé le profil d’un jeu dans MAKO UI, l’outil respecte ce choix et ne le recrée pas.
- Si une bibliothèque est temporairement hors ligne (par exemple un disque externe non branché), les réglages de ces jeux restent inchangés.

### 7. Lancer les jeux depuis la liste

Chaque ligne comporte un bouton « ▶ Lancer » qui démarre le jeu via Steam. Pendant que le jeu tourne, le bouton indique « En cours ».

### 8. Affichage en direct des fonctions MAKO réellement utilisées

La colonne « Fonctions MAKO actives » se met à jour toutes les 3 secondes. Elle montre ce que MAKO a **réellement appliqué** dans le jeu, et non ce que dit le fichier de configuration :

- **Génération d’images** : multiplicateur fixe (par exemple ×2) ou mode adaptatif (FPS cible et multiplicateur maximal), échelle Flow et mode performance.
- **Mise à l’échelle** : méthode et résolution (par exemple 1280×720 → 2560×1440), suréchantillonnage.
- **Autres couches** : vkBasalt, Zink, audio ALSA.
- **Modifications en attente**, comme « redémarrage du jeu nécessaire » ou « reconstruction de la swapchain nécessaire », ainsi que les erreurs signalées par MAKO.

Si Mako FG est installé pour un jeu mais que MAKO n’est pas réellement chargé, c’est aussi indiqué, pour vous aider à trouver le problème.

### 9. Incrustation au lancement d’un jeu

Si l’Assistant MAKO est ouvert quand vous lancez un jeu, dès qu’il détecte que MAKO fonctionne dans le jeu, il affiche les fonctions MAKO actives en bas à droite pendant environ 10 secondes, puis les fait disparaître en fondu :

- L’incrustation apparaît une fois par lancement, ne prend jamais le focus du clavier ou de la souris, et laisse passer les clics.
- Elle peut s’afficher par-dessus les jeux Proton en plein écran.
- Si un jeu avec Mako FG installé n’a toujours pas chargé MAKO 90 secondes après son lancement, un avertissement s’affiche à la place.
- Vous pouvez la désactiver avec la case « Incrustation au lancement » de la barre d’outils.

### 10. Recherche et filtres

- Recherche par nom de jeu (dans n’importe quelle langue) ou par App ID.
- Filtres : tous les jeux, Mako FG installé, Mako FG non installé, réglages MAKO uniquement, en cours d’exécution.

### 11. Douze langues d’interface

台灣正體中文, 简体中文, English, 日本語, Deutsch, Français, Español, Italiano, ไทย, Tiếng Việt, Bahasa Melayu, हिन्दी.

Au premier lancement, la langue suit celle du système. Vous pouvez la changer à tout moment en haut à droite ; le changement s’applique immédiatement et est mémorisé.

### 12. Conçu pour la sécurité

- `conf.toml` et le `localconfig.vdf` de Steam sont sauvegardés (`*.mako-assistant.bak`) avant chaque modification.
- Après l’écriture de `conf.toml`, l’outil le vérifie avec `mako-cli validate`. Si MAKO le refuse, le fichier d’origine est restauré automatiquement.
- `localconfig.vdf` n’est jamais modifié directement pendant que Steam tourne.
- Quand vous cliquez sur « Installer Mako FG », l’outil vérifie d’abord que MAKO Renderer est installé (`~/.local/bin/mako-launch` existe) et que MAKO UI a créé ses réglages. Si l’un des deux manque, rien n’est modifié et l’outil vous invite à installer MAKO d’abord.

## Installer l’Assistant MAKO

**AppImage (recommandé)** : Python et Qt sont inclus, rien d’autre n’est à installer.

```bash
chmod +x MAKO_Assistant-*-x86_64.AppImage
./MAKO_Assistant-*-x86_64.AppImage
```

**Depuis les sources** : nécessite Python 3.11 ou plus récent et PyQt6 (Arch : `sudo pacman -S python-pyqt6`).

```bash
./mako-assistant    # lancer directement
./install.sh        # installer dans ~/.local/share/mako-assistant et ajouter une entrée au menu des applications
```

## Limites connues

- **L’incrustation n’apparaît pas en mode Jeu du Steam Deck (gamescope).** Sur Steam Deck, utilisez plutôt le plugin Decky de MAKO.
- Les jeux en plein écran exclusif sous Wayland natif peuvent masquer l’incrustation.
- Les options de lancement ne peuvent être modifiées en direct que via le port du client Steam ouvert par Decky Loader (8080). Sans Decky, fermez Steam avant d’appliquer, ou laissez l’outil fermer et redémarrer Steam.
- L’affichage des fonctions réellement utilisées et les métadonnées de profil MAKO sont lus au format de la version actuelle de MAKO. Après une mise à jour majeure de MAKO ou de Steam, ils peuvent ne plus s’afficher temporairement (vous voyez « — »), mais l’installation et la suppression continuent de fonctionner.
- En thaï, vietnamien, malais et hindi, les menus contextuels sont en anglais (Qt n’a pas de traduction officielle pour ces langues). Steam n’a pas de noms de jeux en malais ni en hindi : ces deux langues affichent toujours les noms d’origine.
- Seule la sauvegarde la plus récente est conservée.

## Où sont stockées les données

| Emplacement | Contenu |
|---|---|
| `~/.config/mako-assistant/state.json` | État propre à l’Assistant MAKO : cache de la liste des jeux, jeux installés avec cet outil, langue de l’interface, réglage de l’incrustation |
| `~/.config/mako-render/conf.toml` | Réglages de MAKO Renderer (profils de jeu) |
| `~/.config/mako-render/profile-metadata.json` | Métadonnées des profils MAKO (noms des jeux, App ID Steam) |
| `<Steam>/userdata/<ID utilisateur>/config/localconfig.vdf` | Options de lancement Steam |
