# Wayfarer

Wayfarer builds trip itineraries on your computer and exports them as posters. Works offline. Sends no data.

## Download

1. Open the [Releases page](https://github.com/TariqMK/Wayfarer/releases).
2. Download the file for your computer:
   - Windows x64: `Wayfarer-vX.Y.Z-windows-x64.exe`
   - macOS Apple Silicon: `Wayfarer-vX.Y.Z-macos-arm64.zip`
   - Linux x64: `Wayfarer-vX.Y.Z-linux-x64.tar.gz`
3. Put the app in a folder you can change, for example a folder in Documents. Wayfarer stores your data next to it.
4. Open the file. Wayfarer does not need an installer.

**Caution:** Do not put Wayfarer in `Program Files` or another protected folder. It can't save trips there.

**Note:** Builds are unsigned. Windows can show a warning the first time. Select **More info**, then **Run anyway**.

**Note:** On macOS, approve the app the first time under System Settings > Privacy & Security. Move `Wayfarer.app` out of Downloads before you open it. macOS can otherwise run it from a temporary read-only location.

**Note:** Windows needs the Microsoft Edge WebView2 Runtime. Windows 11 includes it. Linux needs GTK 3 and WebKit2GTK 4.1.

## Plan a trip

1. Select **New trip**.
2. Enter the **Trip title**, **Subtitle** and **Trip notes**.
3. Select **Add day**. Each new day gets the date after the previous day.
4. Select **Add entry** in **Morning**, **Afternoon** or **Evening**.
5. Set the **Type**, **From**, **To**, **Duration** and **Notes**.
6. Select **Overnight** for an entry that continues into the next day.
7. Select **Done**.
8. Select **Save**, or press Ctrl+S.

Each type has its own line style on the route:

| Type | Line |
|---|---|
| Flight | Long dashes |
| Train | Rail track |
| Drive, Taxi | Thick solid |
| Bus | Thin solid |
| Walk | Small dots |
| Hike | Large dots |
| Boat | Wave |
| Cycle | Short dashes |
| Motorbike | Dash and dot |
| Stop or note | Faint line |

### Change the order

- Drag an entry to another position, part of the day or day.
- Drag a day by its grip to move the whole day.
- Without a mouse: select an entry and use **Move up** or **Move down**. On a day, use the up and down arrows.

### Undo a deletion

**Delete entry** and **Remove day** show **Undo** for 6 seconds. Deleted items are not removed from the saved file until you select **Save**.

## Export a trip

1. Select **Preview** to see the poster.
2. Select **Export**.
3. Set **Format**: **PDF**, **Image** or **Text**.
4. Set **Poster style**. **Route line** is the default.
   - **Route line**: the trip as one line, in the style of a rail map.
   - **Survey sheet**: a map sheet with contour lines, in two columns.
   - **Ticket stack**: each entry as a ticket.
5. Set **Appearance**: **Light** or **Dark**.
6. Select **Export**. The Save dialog opens in `WayfarerData\exports`.
7. Select **Save**.

**Caution:** Dark posters use a lot of ink. Use **Light** to print.

- **PDF** gives A4 pages. Long trips continue on more pages.
- **Image** gives one PNG image.
- **Text** gives a plain text file. **Copy** puts the same text on the clipboard.

The poster style you select in **Preview** is saved with the trip.

## Check for updates

1. Select the version number next to **Wayfarer** in the header.
2. Read the result. If a newer version exists, select **Open release page**.

Wayfarer does not download or install anything.

## Privacy

- Wayfarer works offline. All fonts, icons and libraries are inside the app.
- There are no accounts, telemetry, tracking or analytics.
- All your data is in one folder, `WayfarerData`, next to the app. On macOS it is next to `Wayfarer.app`.
  - `trips`: your saved trips
  - `exports`: where the Save dialog opens. A file goes elsewhere only if you choose a different folder in the dialog.
  - `webview`: the working files of the app's window. The app removes this folder when it closes.
- Wayfarer stores no user data in your user profile.
- **Caution:** The system unpacks the Windows and Linux app to the temporary folder while it runs. These are program files, not your data. The app removes them when it closes.
- **Note:** On macOS, the system's web view can keep its own working files in your Library folder. The app can't move these files. Your trips and exports are not in them.
- Wayfarer makes one network connection, and only when you ask. When you select the version number, the app asks GitHub (api.github.com) for the latest release. It sends nothing else and nothing is downloaded.

## Move or back up your data

1. Close Wayfarer.
2. Copy or move the `WayfarerData` folder together with the app.

**Caution:** If you move only the app, it starts with an empty `WayfarerData` folder. If you delete the folder, you delete your trips.

## Limitations

- There is no general undo. **Undo** covers only the last deleted entry or day.
- **Image** and **PDF** exports are pictures of the poster. You cannot select the text in them.
- A saved trip has one file. Wayfarer does not sync trips between computers.

## Run from source

Requires Python 3.11 or later.

```bash
python -m venv venv
```

```bash
venv\Scripts\python -m pip install -e ".[dev]"
```

```bash
venv\Scripts\python -m wayfarer
```

On macOS and Linux, use `venv/bin/python`. On Linux, also install `PyGObject` and the GTK packages listed in the note in [Download](#download).

From source, the data folder is `WayfarerData` in the project root. Git ignores it.

### Run the tests

```bash
venv\Scripts\python -m pytest
```

### Check the code

```bash
venv\Scripts\python -m ruff check wayfarer tests
```

### Build the app

```bash
venv\Scripts\pyinstaller --noconfirm Wayfarer.spec
```

The build is in `dist/`.

## Creating a Release

1. Open **Actions** > **Release** on GitHub.
2. Select **Run workflow** on the `main` branch.
3. Set **Draft or public release**. A draft is visible only to the repository owner until published.
4. Set **Version increase**: **patch**, **minor** or **major**.
5. Select **Run workflow**.

The workflow finds the highest version in the existing tags and releases, including drafts, and adds the increase. It runs the tests first. It creates the tag and release only after all three builds succeed. It never commits to a branch. The source always holds the development version `0.0.0.dev0`.

No secrets are needed. The workflow uses the token that GitHub supplies.

## Credits

- [html2canvas](https://github.com/niklasvh/html2canvas), MIT licence.
- [Lucide](https://lucide.dev) icons, ISC licence.
- IBM Plex Sans, IBM Plex Mono, Figtree, Newsreader, DM Sans and DM Mono from [Fontsource](https://fontsource.org), SIL Open Font License.
