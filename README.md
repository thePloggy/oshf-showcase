# #OpenSourceHiggsfield — community showcase

**Live page: https://theploggy.github.io/oshf-showcase/**

An unofficial community page (not affiliated with Comfy Org) that shows every project submitted to the #OpenSourceHiggsfield threads in one place:

- a screenshot, the title, author and description of each project, in random order, in a masonry grid;
- links to the code, the demo and the video when the project has one;
- GitHub stars and forks, GitHub release downloads, and installs from the Comfy Registry when the project is published there;
- filters by function (all-in-one studios, character swap, camera, VFX, 3D, music and lip-sync…) — categories are indicative;
- a community vote: every visitor (one IP address) gets **10 points** to spread across the projects, and can take them back at any time.

## Screenshots and credits

Each screenshot is a reduced copy (640 px wide) of an image taken from the project's own README, shown next to a link to that project. If you are the author and want your image removed or replaced, please [open an issue](https://github.com/thePloggy/oshf-showcase/issues).

## How it works

- The page (`index.html`, `app.js`, `style.css`, `projects.json`, `shots/`) is static and served by GitHub Pages.
- Votes go to a small Python server (`server/server.py`, standard library + SQLite). Visitor IPs are never stored: only an HMAC-SHA256 of the IP with a secret local salt. If the vote server is offline, the page still works and simply hides the vote buttons.
- `tools/` holds the scripts that collected the data from the GitHub API, the READMEs and the Comfy Registry API. Duplicate submissions of the same repository are merged into one card.

Data snapshot: 12 November 2026.
