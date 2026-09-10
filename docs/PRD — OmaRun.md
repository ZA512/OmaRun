# PRD — OmaRun

**Nom de travail :** OmaRun  
**Alternative de nom :** Script Deck  
**Plateforme cible :** Omarchy / Quickshell  
**Type :** plugin `bar-widget` avec panel  
**Version ciblée :** MVP / V1

---

# 1. Vision produit

OmaRun est un plugin Omarchy permettant d’enregistrer, lancer, planifier et contrôler de petites commandes ou scripts personnels sans avoir à ouvrir un terminal.

L’objectif n’est pas de remplacer un terminal, cron, systemd ou un ordonnanceur professionnel.

OmaRun doit servir d’interface légère entre l’utilisateur et les scripts qu’il utilise régulièrement.

Exemples :

- synchroniser une bibliothèque de séries ;
- ranger des films ;
- lancer une sauvegarde ;
- synchroniser un dossier ;
- exécuter un script Python ;
- lancer ponctuellement une commande ;
- automatiser périodiquement l’une de ces commandes.

Le produit doit donner l’impression d’être un **launcher Omarchy auquel on a ajouté juste ce qu’il faut d’automatisation et de supervision**.

---

# 2. Principe UX fondamental

## Minimal au repos, puissant à la demande

L’interface principale ne doit jamais ressembler à un dashboard d’administration ou à un gestionnaire de tâches systemd.

Quand l’utilisateur clique sur OmaRun, il doit principalement voir :

- le nom de ses scripts ;
- leur état général ;
- un bouton permettant de les lancer.

Tout le reste doit être révélé progressivement.

Hiérarchie d’information :

**Niveau 1 — visible en permanence**

Nom du script  
État visuel  
Présence éventuelle d’une automatisation  
Bouton Run

**Niveau 2 — visible au survol ou au focus clavier**

Date relative de dernière exécution  
État détaillé éventuel  
Menu d’actions secondaires

**Niveau 3 — visible après ouverture du script**

Résultat de la dernière exécution  
Logs  
Durée  
Exit code  
Date exacte  
État du timer  
Prochaine exécution  
Actions de gestion

**Niveau 4 — configuration**

Commande  
Arguments  
Planification  
Répertoire de travail  
Timeout  
Variables d’environnement  
Autres options avancées

Aucune information de niveau 3 ou 4 ne doit encombrer la liste principale.

---

# 3. Objectif de la V1

La V1 doit résoudre parfaitement quatre besoins :

1. enregistrer une commande ;
2. la lancer manuellement ;
3. éventuellement la lancer automatiquement ;
4. savoir facilement si sa dernière exécution s’est correctement déroulée.

Tout ce qui ne contribue pas directement à ces quatre objectifs doit être considéré comme secondaire.

---

# 4. Non-objectifs

La V1 ne doit PAS devenir :

- un terminal embarqué complet ;
- un éditeur de scripts ;
- une interface graphique générique pour systemd ;
- un remplaçant de cron complet ;
- un système de monitoring ;
- un gestionnaire de pipelines ;
- un ordonnanceur avec dépendances complexes ;
- un système centralisé de logs ;
- une interface d’administration distante.

Ne pas ajouter de fonctionnalités simplement parce qu’elles sont techniquement possibles.

---

# 5. Widget dans la barre Omarchy

Le widget doit être extrêmement discret.

Exemple :

`>_`

ou une icône évoquant Run / Terminal / Automation.

Le widget ne doit pas afficher en permanence le nombre de scripts ou leurs états.

Exception importante : une information exceptionnelle peut être signalée.

Exemples :

`>_` → état normal

`>_ •` → au moins une tâche est actuellement en cours

`>_ !` → au moins une tâche automatique a échoué depuis que l’utilisateur a consulté OmaRun

Le plugin doit donc fonctionner selon le principe :

**silence lorsque tout va bien, visibilité lorsqu’une intervention peut être nécessaire.**

Cliquer sur l’icône ouvre le panel.

---

# 6. Panel principal

Le panel principal doit être petit et immédiatement compréhensible.

Exemple conceptuel :

```text
┌───────────────────────────────────┐
│ OmaRun                         +  │
├───────────────────────────────────┤
│ ●  Sync séries            ⏱   ▶  │
│ ●  Sync films                  ▶  │
│ ●  Backup NAS             ⏱   ▶  │
│ ●  Clean downloads        ⏱   ▶  │
└───────────────────────────────────┘
```

C’est l’état normal de l’interface.

Aucun log.

Aucun chemin.

Aucune commande.

Aucun exit code.

Aucune heure.

Aucune description de timer.

---

# 7. Signification des éléments d’une ligne

Chaque tâche contient quatre informations maximum dans son état normal.

### État

Petit indicateur discret placé à gauche.

États :

- gris : jamais exécuté ;
- vert : dernière exécution réussie ;
- rouge : dernière exécution échouée ;
- animation ou état spécifique : en cours.

Les couleurs doivent utiliser autant que possible les tokens/thèmes Omarchy plutôt que des couleurs codées en dur.

### Nom

Nom libre donné par l’utilisateur.

Exemples :

`Sync séries`

`Backup NAS`

`Update library`

### Automatisation

Une petite icône horloge apparaît uniquement lorsque la tâche possède une planification active.

Elle ne doit pas afficher son planning dans la liste.

Un tooltip peut indiquer :

`Toutes les 6 heures`

ou :

`Tous les jours à 03:00`

### Run

Le bouton Run doit rester visible en permanence.

Il ne doit PAS apparaître uniquement au survol.

Le lancement d’un script doit toujours résulter d’une action explicite sur ce bouton.

Cliquer sur la ligne ne doit jamais lancer la commande.

---

# 8. Comportement au survol

Le survol doit enrichir la ligne sans complètement la transformer.

Exemple :

```text
● Sync séries    OK · il y a 2 h   ⏱  ▶  ⋯
```

Les informations secondaires peuvent remplacer temporairement de l’espace libre disponible.

Le menu `⋯` apparaît au survol ou au focus clavier.

Il contient au maximum :

```text
Run
Details
Edit
Enable/Disable schedule
Delete
```

Ne pas multiplier les boutons directement dans la ligne.

Le menu est destiné aux actions peu fréquentes.

---

# 9. Tâche en cours

Lorsqu’une commande s’exécute :

```text
◉ Sync séries          Running…   ■
```

Le bouton Run devient Stop.

L’animation doit rester discrète.

Un clic sur la ligne permet d’ouvrir la sortie en cours d’exécution.

OmaRun ne doit jamais lancer une seconde instance de la même tâche si la première est encore active.

---

# 10. Consultation d’une tâche

Cliquer sur le nom ou sur la ligne ouvre une vue détaillée.

Cette vue doit rester beaucoup plus orientée « résultat » que « configuration ».

Exemple :

```text
← Sync séries

✓ Success
Aujourd'hui 14:32 · 18 s

────────────────────────────────

Analyse de /mnt/media/inbox
12 fichiers détectés
4 épisodes déplacés
2 séries mises à jour
Terminé.

────────────────────────────────

Exit 0                         ⧉

Next run
Aujourd'hui 20:32

                     Run again
```

La zone principale est le résultat du script.

L’utilisateur est venu ici principalement pour répondre à :

**« Qu’est-ce que mon script a fait ? »**

et éventuellement :

**« Pourquoi a-t-il échoué ? »**

---

# 11. Logs

La V1 ne doit conserver qu’une seule sortie complète par tâche : celle de la dernière exécution terminée.

Pendant une exécution, OmaRun peut afficher la sortie courante en temps réel.

Les sorties stdout et stderr peuvent être fusionnées chronologiquement pour préserver l’ordre de lecture.

À la fin de l’exécution, conserver :

```text
last.log
status.json
```

`status.json` contient au minimum :

```json
{
  "status": "success",
  "exitCode": 0,
  "startedAt": "...",
  "finishedAt": "...",
  "durationMs": 12340
}
```

Le bouton Copy copie l’intégralité de `last.log`.

Ne pas intégrer dans la V1 un navigateur complexe d’historique des logs.

---

# 12. Création d’une tâche

C’est un point critique du projet.

L’écran de création ne doit surtout pas présenter vingt options immédiatement.

L’utilisateur qui veut simplement enregistrer :

```text
python /home/user/scripts/media.py
```

doit pouvoir le faire en quelques secondes.

Premier écran :

```text
New command

Name
[ Sync séries                         ]

Command
[ python /home/user/scripts/media.py  ]

                         [ Cancel ] [ Add ]
```

C’est suffisant pour créer une tâche manuelle.

Sous les champs principaux :

```text
○ Run automatically

▸ Advanced
```

Les options supplémentaires n’apparaissent que lorsqu’elles sont demandées.

---

# 13. Configuration de l’automatisation

Lorsque `Run automatically` est activé, la section se déplie.

Ne jamais présenter directement une syntaxe cron ou systemd.

Interface proposée :

```text
Run automatically          ●

Run
[ Every ▼ ]

[ 6 ] [ Hours ▼ ]

Next run: Today at 20:32
```

Modes V1 :

```text
Every X minutes
Every X hours
Every X days

Every day at HH:MM

Every week
    [Mon] [Tue] [Wed] [Thu] [Fri] [Sat] [Sun]
    at HH:MM
```

Les choix naturels de l’utilisateur sont ensuite traduits en timer systemd.

Le terme `systemd` n’a pas besoin d’être visible dans l’interface principale.

---

# 14. Modification de l’automatisation

La planification doit pouvoir être :

- activée ;
- désactivée ;
- modifiée ;

sans supprimer la tâche.

Lorsque le planning est actif, afficher dans la page Details :

```text
Schedule
Every 6 hours

Next run
20:32
```

Éventuellement :

```text
Edit
```

Une tâche peut donc exister indépendamment de son timer.

---

# 15. Options avancées

La section `Advanced` est fermée par défaut.

Elle peut contenir en V1 :

```text
Working directory
[                              ]

Arguments
[                              ]

Timeout
[ No timeout ▼ ]

Environment variables
[                              ]
```

Il faut privilégier une exécution sans shell intermédiaire lorsque c’est possible.

Les commandes et arguments doivent être gérés de façon suffisamment robuste pour éviter qu’une concaténation naïve de chaînes entraîne des comportements imprévus.

Si une future version autorise explicitement des fonctionnalités shell comme :

```text
|
>
&&
;
$()
```

cela devra être présenté comme un mode distinct, clairement identifié comme exécution via shell.

---

# 16. Architecture d’exécution

Principe impératif :

**une tâche manuelle et une tâche automatique doivent utiliser exactement le même chemin d’exécution.**

Ne pas implémenter :

```text
UI → script

systemd → autre mécanisme → script
```

Préférer :

```text
                    ┌──── Manual Run
                    │
                    ▼
             systemd user service
                    ▲
                    │
                    └──── systemd timer
                           │
                           ▼
                      OmaRun Runner
                           │
                           ▼
                        command
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
           last.log                 status.json
```

Même une tâche exclusivement manuelle possède son service user systemd.

Le timer est facultatif.

Ainsi :

- Run utilise le service ;
- Stop utilise le service ;
- les timers utilisent le même service ;
- l’état est cohérent ;
- les doubles exécutions sont évitées ;
- le comportement manuel et automatique reste identique.

---

# 17. Backend OmaRun

Le plugin peut contenir un petit backend/helper chargé de :

- lire et écrire la configuration ;
- créer les services systemd user ;
- créer/modifier/supprimer les timers ;
- déclencher les services ;
- arrêter les services ;
- récupérer leur état ;
- exécuter le runner ;
- écrire les logs ;
- écrire les métadonnées d’exécution.

Le frontend QML ne doit pas contenir toute la logique métier.

Architecture recommandée :

```text
BarWidget.qml
Panel.qml

components/
    TaskRow.qml
    TaskDetails.qml
    TaskEditor.qml
    ScheduleEditor.qml
    LogViewer.qml

backend/
    omarunctl.py
    runner.py
```

Le découpage exact peut évoluer, mais maintenir une séparation claire entre UI et gestion des tâches.

---

# 18. Stockage

Configuration utilisateur proposée :

```text
~/.config/omarun/
```

avec par exemple :

```text
tasks.json
```

État et logs :

```text
~/.local/state/omarun/
```

Exemple :

```text
~/.local/state/omarun/tasks/sync-series/
    last.log
    status.json
```

Units systemd :

```text
~/.config/systemd/user/
    omarun-sync-series.service
    omarun-sync-series.timer
```

Les identifiants internes doivent être stables et distincts du nom visible afin qu’un renommage de :

`Sync séries`

vers :

`Ranger mes séries`

ne nécessite pas de recréer toute la tâche.

Utiliser par exemple un UUID ou un slug interne immuable.

---

# 19. Écriture des logs

Pendant l’exécution :

```text
current.log
```

À la fin, le résultat devient :

```text
last.log
```

Éviter de supprimer le dernier résultat valide dès le démarrage d’une nouvelle commande.

Une stratégie acceptable consiste à écrire dans un fichier temporaire puis effectuer un remplacement atomique lorsque l’exécution est terminée.

Si la tâche est actuellement en cours, la vue Details peut afficher `current.log`.

Si elle est terminée, elle affiche `last.log`.

---

# 20. Gestion des erreurs

OmaRun doit distinguer :

### Échec de la commande

Exemple :

```text
Exit code 1
```

→ tâche rouge.

### Commande inexistante

Exemple :

```text
Executable not found
```

→ erreur explicite compréhensible.

### Working directory inexistant

→ ne pas lancer la tâche.

### Timeout

→ état spécifique :

```text
Timed out after 30 min
```

### Arrêt manuel

Ne pas afficher comme une erreur générique.

Utiliser par exemple :

```text
Stopped by user
```

### Configuration systemd invalide

Afficher une erreur OmaRun compréhensible plutôt que simplement la sortie brute de systemctl.

Une section secondaire peut cependant afficher le détail technique.

---

# 21. Notifications

La V1 peut intégrer des notifications desktop.

Comportement par défaut recommandé :

```text
Manual runs:
    aucune notification

Scheduled runs:
    notification uniquement en cas d'échec
```

Raison :

une tâche automatique qui fonctionne ne doit pas déranger l’utilisateur.

Exemple :

```text
OmaRun

Sync séries failed
Exit code 1
```

Cliquer sur la notification pourra idéalement ouvrir OmaRun sur la tâche concernée si l’API Omarchy le permet proprement.

---

# 22. Barre et gestion des erreurs

Lorsqu’une tâche planifiée échoue, OmaRun peut afficher un indicateur discret sur son widget.

L’indicateur reste présent jusqu’à ce que l’utilisateur consulte la tâche concernée.

Il ne faut pas transformer la barre en centre de notifications.

Une tâche manuelle ayant échoué ne nécessite pas forcément un badge permanent puisque l’utilisateur vient lui-même de déclencher l’action.

---

# 23. Recherche

Ne pas afficher systématiquement une barre de recherche.

Pour quatre scripts, elle serait inutile et alourdirait le produit.

Prévoir néanmoins l’architecture pour pouvoir l’ajouter lorsque le nombre de tâches devient important.

Une future règle pourrait être :

```text
moins de 8 tâches → aucune recherche visible

8 tâches ou plus → champ de recherche
```

Ne pas obligatoirement implémenter cette fonctionnalité en V1.

---

# 24. Clavier

Même si OmaRun est principalement pensé comme panel graphique, il doit fonctionner correctement au clavier.

Objectif :

```text
↑ ↓     sélectionner une tâche
Enter   ouvrir Details
Space   Run
Esc     retour / fermer
```

Éviter d’introduire beaucoup de raccourcis supplémentaires dans la V1.

---

# 25. Suppression d’une tâche

La suppression doit :

1. arrêter proprement la tâche si elle tourne ;
2. désactiver son timer ;
3. supprimer les unités systemd générées ;
4. recharger la configuration systemd utilisateur ;
5. supprimer sa configuration OmaRun.

Concernant le dernier log, OmaRun peut le supprimer avec la tâche.

Une confirmation est nécessaire.

Exemple :

```text
Delete "Sync séries"?

This removes its schedule and OmaRun logs.
Your script itself will not be deleted.

Cancel    Delete
```

Il est essentiel de préciser que **le script source n’est jamais supprimé**.

---

# 26. Édition d’une tâche

Modifier une tâche ne doit pas casser son identité.

Si le nom change, conserver le même ID interne.

Si la commande ou la planification change :

- mettre à jour les fichiers nécessaires ;
- effectuer `daemon-reload` si nécessaire ;
- réactiver proprement le timer s’il était actif.

Une tâche en cours d’exécution ne doit idéalement pas voir sa configuration changée sous ses pieds.

Dans ce cas, soit empêcher temporairement l’édition, soit appliquer la nouvelle configuration uniquement à la prochaine exécution.

Choisir le comportement le plus sûr et le plus simple.

---

# 27. Sécurité

Les plugins Omarchy s’exécutant dans le contexte utilisateur, OmaRun doit être considéré comme un composant capable d’exécuter arbitrairement les commandes enregistrées.

Principes :

- aucune élévation automatique de privilèges ;
- aucun `sudo` ajouté implicitement ;
- aucun téléchargement ou exécution de code distant ;
- éviter `shell=True` ou `bash -c` par défaut ;
- aucun secret affiché volontairement dans l’interface ;
- variables d’environnement sensibles à traiter avec prudence ;
- fichiers créés avec des permissions adaptées ;
- validation des identifiants utilisés dans les noms de fichiers systemd ;
- ne jamais construire un nom de fichier système directement depuis le nom visible d’une tâche.

OmaRun exécute ce que l’utilisateur lui demande.

Il ne cherche pas à contourner les mécanismes de sécurité du système.

---

# 28. Style visuel

OmaRun doit visuellement donner l’impression d’être une fonctionnalité native d’Omarchy.

Utiliser autant que possible :

- les composants existants ;
- les espacements existants ;
- les tokens de thème ;
- les comportements des autres panels ;
- les animations déjà utilisées par Omarchy.

Éviter :

- les cartes dans des cartes dans des cartes ;
- les bordures inutiles ;
- les gros titres ;
- les tableaux ;
- les formulaires très longs ;
- les couleurs codées en dur ;
- les badges partout.

L’espace vide est volontaire.

---

# 29. Progressive disclosure

Cette règle doit guider toute décision UI.

Avant d’ajouter une information à l’écran principal, poser la question :

**« L’utilisateur a-t-il besoin de cette information pour choisir ou lancer son script maintenant ? »**

Si la réponse est non :

ne pas l’afficher par défaut.

Avant d’ajouter un champ à l’écran de création :

**« Ce champ est-il indispensable pour créer une tâche manuelle fonctionnelle ? »**

Si la réponse est non :

le placer sous Automation ou Advanced.

---

# 30. Critères de réussite UX

Le produit est réussi si un nouvel utilisateur peut comprendre spontanément :

```text
cliquer OmaRun
      ↓
voir ses scripts
      ↓
cliquer ▶
      ↓
le script tourne
```

sans documentation.

Il doit également comprendre naturellement :

```text
cliquer sur Sync séries
      ↓
voir ce qui s'est passé
```

et :

```text
+
↓
Nom
Commande
Add
```

La création d’une tâche manuelle ne doit pas exposer les mécanismes internes systemd.

---

# 31. MVP fonctionnel obligatoire

La première version livrable doit impérativement inclure :

- widget Omarchy ;
- panel ;
- liste des tâches ;
- création d’une tâche ;
- modification ;
- suppression ;
- Run ;
- Stop ;
- statut Running ;
- réussite/échec ;
- dernière sortie ;
- stdout/stderr ;
- Copy ;
- exit code ;
- durée ;
- dernière exécution ;
- automation activable ;
- intervalle minutes/heures/jours ;
- horaire quotidien ;
- jours de semaine + horaire ;
- prochaine exécution ;
- timers systemd user ;
- notification en cas d’échec d’une tâche automatique ;
- prévention du double lancement ;
- working directory ;
- arguments ;
- timeout.

Cette liste constitue la limite haute de la V1.

Ne pas ajouter automatiquement les fonctionnalités décrites dans la section suivante.

---

# 32. Fonctionnalités prévues pour plus tard

À conserver comme pistes, mais hors MVP :

- historique des cinq ou dix dernières exécutions ;
- retry automatique ;
- condition « seulement si réseau disponible » ;
- condition « seulement si chemin monté » ;
- lancement au login ;
- dépendances entre tâches ;
- groupes ;
- favoris ;
- drag & drop ;
- import/export ;
- paramètres prédéfinis d’un script ;
- boutons d’arguments ;
- mode dry-run ;
- commandes shell complexes ;
- templates ;
- recherche ;
- filtre erreurs ;
- durée moyenne ;
- statistiques ;
- intégration SSH ;
- lancement sur une machine distante.

Ne pas anticiper ces fonctionnalités dans l’UI.

L’architecture doit simplement éviter de rendre leur ajout impossible.

---

# 33. Point important : ne pas sur-concevoir

OmaRun vise des utilisateurs techniques mais ne doit pas utiliser cette excuse pour proposer une mauvaise UX.

Un utilisateur capable d’écrire :

```bash
python ~/scripts/serieranger.py
```

n’a pas nécessairement envie de manipuler :

```text
ExecStart
OnUnitActiveSec
WantedBy
systemctl
journalctl
```

OmaRun doit masquer cette mécanique sauf lorsqu’un problème nécessite réellement de la montrer.

L’utilisateur doit manipuler des concepts :

```text
Commande
Lancer
Tous les jours
Toutes les 6 heures
Dernier résultat
Erreur
```

et non l’implémentation technique.

---

# 34. Philosophie produit

OmaRun ne doit pas chercher à impressionner par le nombre de fonctions.

Sa valeur vient du fait qu’un geste actuellement pénible :

```text
ouvrir terminal
↓
retrouver la commande
↓
la lancer
↓
attendre
↓
lire la sortie
```

devient :

```text
OmaRun
↓
▶
```

et qu’un second besoin :

```text
penser régulièrement à lancer le script
```

devient :

```text
Run automatically
Every 6 hours
```

Puis OmaRun disparaît du chemin de l’utilisateur.

C’est cette simplicité qui doit guider toutes les décisions de conception.

---

# 35. Ordre de développement recommandé à l’agent

Ne pas commencer par l’écran de configuration complet.

Développer dans cet ordre :

**Phase 1 — vertical slice manuel**

Widget → panel → une tâche → Run → résultat → status.

Valider réellement une exécution de bout en bout.

**Phase 2 — persistance**

Création → sauvegarde → édition → suppression.

**Phase 3 — runner**

Logs propres → exit code → durée → erreurs → Stop → protection double lancement.

**Phase 4 — systemd**

Service user commun au lancement manuel et automatique.

**Phase 5 — timers**

Création → activation → modification → désactivation → prochaine exécution.

**Phase 6 — polish UX**

Hover → focus clavier → animations → tooltips → empty states → erreurs → thème Omarchy.

Ne pas construire l’intégralité du backend avant d’avoir validé le vertical slice UI + exécution.

---

# 36. Première expérience

Lorsqu’aucune tâche n’existe :

```text
┌───────────────────────────────────┐
│ OmaRun                         +  │
├───────────────────────────────────┤
│                                   │
│       No commands yet             │
│                                   │
│    Add the scripts and commands   │
│    you use regularly.             │
│                                   │
│         + Add command             │
│                                   │
└───────────────────────────────────┘
```

L’empty state doit être chaleureux mais court.

Pas de tutoriel de six étapes.

---

# 37. Critères d’acceptation V1

La V1 peut être considérée comme fonctionnelle lorsque le scénario suivant fonctionne sans terminal :

```text
1. Installer OmaRun.
2. Ajouter "Sync séries".
3. Indiquer la commande Python correspondante.
4. Sauvegarder.
5. Voir "Sync séries" dans la liste.
6. Cliquer ▶.
7. Voir la tâche passer en Running.
8. Attendre la fin.
9. Voir son état passer au vert ou rouge.
10. Ouvrir la tâche.
11. Lire la sortie.
12. Copier cette sortie.
13. Activer "Run automatically".
14. Choisir "Every 6 hours".
15. Fermer OmaRun.
16. Le timer déclenche la même tâche.
17. Une exécution réussie reste silencieuse.
18. Une exécution automatique échouée déclenche une notification.
19. OmaRun indique l'échec dans son widget.
20. L'utilisateur ouvre OmaRun et comprend immédiatement quelle tâche a échoué.
```

Si ce scénario est fluide, le MVP est réussi.

---

# 38. Directive finale à l’agent de développement

Prioriser dans cet ordre :

**simplicité UX > cohérence Omarchy > robustesse > fonctionnalités.**

Ne pas ajouter d’élément permanent à l’interface simplement parce qu’une donnée est disponible.

Ne pas exposer systemd sauf pour diagnostic.

Ne pas transformer OmaRun en terminal.

Ne pas transformer OmaRun en dashboard.

Ne pas transformer OmaRun en gestionnaire cron.

Le produit doit rester un **petit launcher de commandes extrêmement agréable**, capable en plus de lancer certaines d’entre elles automatiquement et de dire simplement si elles ont fonctionné.