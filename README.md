# OmaRun

Plugin Omarchy `bar-widget` avec panel et backend Python pour piloter des commandes via services/timers `systemd --user`.
Le panel appelle directement `backend/omarunctl.py` via `Process` (`list`, `add`, `run`, `stop`, `status`, `log`).

## Installation

Depuis une session Omarchy graphique, installez et activez le plugin avec :

```sh
omarchy plugin add https://github.com/ZA512/OmaRun.git --enable
```

La commande clone le dépôt dans `~/.config/omarchy/plugins/io.github.mgirard.omarun`,
valide son manifeste, puis ajoute le widget à la barre. Omarchy propose son
emplacement ; choisissez `right` pour le placer à droite.

Après une mise à jour du dépôt, installez la dernière version avec :

```sh
omarchy plugin update io.github.mgirard.omarun --yes
```

Pour le désactiver ou le retirer :

```sh
omarchy plugin disable io.github.mgirard.omarun
omarchy plugin remove io.github.mgirard.omarun --yes
```

## Structure

- `manifest.json`
- `BarWidget.qml`
- `Panel.qml`
- `components/`
- `backend/omarunctl.py`
- `backend/runner.py`

## Validation locale

```sh
omarchy plugin validate ~/.config/omarchy/plugins/io.github.mgirard.omarun
qmllint -I "$OMARCHY_PATH/shell" \
  ~/.config/omarchy/plugins/io.github.mgirard.omarun/BarWidget.qml \
  ~/.config/omarchy/plugins/io.github.mgirard.omarun/Panel.qml
```

## Backend CLI

```sh
python3 backend/omarunctl.py list
python3 backend/omarunctl.py add --name "Sync séries" --command "python3 /home/user/scripts/sync.py"
python3 backend/omarunctl.py run --id task-xxxxxxxxxxxx
python3 backend/omarunctl.py status --id task-xxxxxxxxxxxx
python3 backend/omarunctl.py update --id task-xxxxxxxxxxxx --name "Sync séries" --command "python3 /home/user/scripts/sync.py"
python3 backend/omarunctl.py log --id task-xxxxxxxxxxxx
python3 backend/omarunctl.py stop --id task-xxxxxxxxxxxx
python3 backend/omarunctl.py delete --id task-xxxxxxxxxxxx
```

Options utiles:

- `--arguments`
- `--working-directory`
- `--timeout-seconds`
- `--env '{"FOO":"bar"}'`
- `--schedule '{"enabled":true,"mode":"every-hours","interval":6}'`

Modes de schedule V1:

- `every-minutes`
- `every-hours`
- `every-days`
- `daily-at` (`time: "HH:MM"`)
- `weekly` (`weekdays: [0..6]`, 0 = lundi)

## Sécurité

- exécution sans shell intermédiaire (`shell=False`);
- aucune élévation de privilèges;
- aucune commande distante implicite.
