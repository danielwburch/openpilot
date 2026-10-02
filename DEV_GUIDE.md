# Daniel's sunnypilot Honda fork: developer guide

This repo is a personal fork of **mvl-boston/openpilot**, branch **sp-honda-202508**
(MVL's Honda/Acura build of sunnypilot). It is set up so you can change the code,
push it to GitHub, and run it on your comma 3X.

---

## 1. What you have

### GitHub repositories (all under github.com/danielwburch)

| Repo | Forked from | Purpose |
|------|-------------|---------|
| `danielwburch/openpilot` | `mvl-boston/openpilot` | Main code. **This is what the device installs.** Must stay named `openpilot` for the installer URL to work. |
| `danielwburch/opendbc` | `mvl-boston/opendbc` | Car ports, CAN definitions, Honda tuning. Pulled in as the `opendbc_repo` submodule. |

Both forks copied every one of MVL's branches (hundreds of them). Harmless, but see
section 9 if you want to delete them.

### Branches

| Branch | What it is | Edit it? |
|--------|------------|----------|
| `sp-honda-202508` | Exact mirror of MVL's branch (commit `550807d`, 2026-09-26). Keep pristine. | No. Use it to diff against / pull MVL changes. |
| `dev` | **Your working branch.** Default branch on GitHub. Starts as `sp-honda-202508` plus a pointer to your own `opendbc` fork. | Yes. This is what you install on the device. |
| `master` | MVL's stale master, copied by the fork. Ignore. | No. |

The `opendbc` fork has the same layout: `sp-honda-202508` (mirror) and `dev` (yours).

### Local clone

`C:\Users\Daniel\Desktop\openpilot` with two remotes:

| Remote | URL | Use |
|--------|-----|-----|
| `origin` | github.com/danielwburch/openpilot | push your work here |
| `mvl` | github.com/mvl-boston/openpilot | fetch MVL's updates from here |

The `opendbc_repo` submodule has the same two remotes (`origin` = yours, `mvl` = MVL's).

### What the code is

- sunnypilot based on **openpilot 0.10.1** (Sept 2025), AGNOS 12.8, Python 3.11/3.12.
- MVL's `sp-honda-202508` is **frozen**: it is the last build that supports comma 3,
  and MVL has said no more updates are planned for it. Newer MVL branches for comma 3X
  are `sp-honda-202607` (release) and `sp-honda-dev-202608` (dev).
- Almost all of MVL's Honda work lives in **opendbc**, not openpilot. The openpilot
  branch history is mostly "repointing opendbc_repo" commits that bump the submodule.

---

## 2. Repository map (where to change things)

| Path | What lives there |
|------|------------------|
| `opendbc_repo/opendbc/car/honda/` | **Honda car port**: `carstate.py` (read CAN), `carcontroller.py` (send steering/gas/brake), `values.py` (car list, limits, tuning), `fingerprints.py`, `hondacan.py` (CAN message builders), `interface.py` (tuning params per model). Most "make my car drive differently" changes go here. |
| `opendbc_repo/opendbc/dbc/` | DBC files: CAN signal definitions. |
| `opendbc_repo/opendbc/safety/` | **Panda safety code** (C). Enforces torque/accel limits in firmware. Changing this changes what the car is physically allowed to do. Be very careful. |
| `selfdrive/controls/` | Lateral and longitudinal control, planners, `controlsd.py`. |
| `selfdrive/modeld/` | Driving model runner. |
| `selfdrive/ui/` | On-device UI (Python/raylib in this version). |
| `sunnypilot/` | sunnypilot-only features: MADS, speed limit control, custom cruise, model selector, sunnylink. |
| `system/manager/` | `manager.py` starts every process; `process_config.py` is the process list; `build.py` runs the on-device compile. |
| `system/updated/updated.py` | The on-device updater (Settings → Software). |
| `launch_chffrplus.sh` | What runs at boot: AGNOS check, overlay update swap, `build.py`, then `manager.py`. |
| `panda/` | Panda firmware submodule (sunnyhaibin/panda). |
| `cereal/` | Message schema (`log.capnp`, `car.capnp`). Add fields here if you need new data between processes. |
| `docs/` | Upstream docs incl. `car-porting/` and `concepts/safety.md`. Read `safety.md`. |

---

## 3. Install your fork on the comma 3X

### Method A: fresh install by URL (recommended first time)

1. Back up anything on the device you want (factory reset wipes drives + settings).
2. Factory reset: Settings → Software → Uninstall, or hold the comma logo during boot.
3. On the setup screen choose **Custom Software** and enter:

   ```
   smiskol.com/fork/danielwburch/dev
   ```

   The installer clones `github.com/danielwburch/openpilot` at branch `dev`.
   (That is why the repo must be named `openpilot`.) To install the pristine MVL
   mirror instead, use `smiskol.com/fork/danielwburch/sp-honda-202508`.

4. Finish the on-screen setup. **First boot compiles the code with scons, which takes
   roughly 15 to 30 minutes** on a comma 3X. The screen shows a progress spinner. Do
   not power it off.

### Method B: switch an existing install over SSH

```bash
cd /data
mv openpilot openpilot.bak        # or rm -rf openpilot
git clone -b dev --recurse-submodules https://github.com/danielwburch/openpilot.git openpilot
cd openpilot && git lfs pull
sudo reboot
```

---

## 4. SSH into the device (you need this for real development)

1. You need an SSH key on your **GitHub account** (the device fetches your public keys
   from GitHub). You currently have no SSH key on this PC. Create one and add it:

   ```bash
   ssh-keygen -t ed25519 -C "burchwdaniel@gmail.com"
   ```

   Then paste the contents of `~/.ssh/id_ed25519.pub` into
   github.com/settings/keys (or run `gh ssh-key add ~/.ssh/id_ed25519.pub`).

2. On the device: Settings → Network → Advanced → **Enable SSH**, then
   **SSH Keys** → Add → enter GitHub username `danielwburch`.

3. Put the device and your PC on the same Wi‑Fi (or tether to the device's hotspot).
   Find the IP under Settings → Network → Advanced.

4. Connect:

   ```bash
   ssh comma@<device-ip>
   ```

   Useful once in:

   ```bash
   tmux a              # watch openpilot's live console output (Ctrl-b then d to detach)
   cd /data/openpilot  # the running code
   git status          # see what branch/commit the device is on
   ```

---

## 5. The development loop

Windows cannot build or run openpilot natively, so the device is your build machine.
Two loops, pick per change:

### Loop 1: edit on the PC, push, pull on the device (clean, keeps history)

```bash
# on the PC, in C:\Users\Daniel\Desktop\openpilot, branch dev
git add <files>
git commit -m "describe the change"
GIT_LFS_SKIP_PUSH=1 git push
```

Then on the device, either:

- **Settings → Software → Check for updates → Download → Reboot**. The updater
  fetches your `dev` branch from `origin`, stages it in `/data/safe_staging`, and swaps
  it in at the next boot. Or
- over SSH: `cd /data/openpilot && git pull && sudo reboot`.

Note: `launch_chffrplus.sh` skips the automatic overlay swap if `/data/openpilot/.git`
was touched by hand (it detects local work and refuses to overwrite it). If you edited
on-device and the Settings updater seems to do nothing, that is why. Use `git pull`.

### Loop 2: edit directly on the device (fastest for trying things)

```bash
ssh comma@<device-ip>
cd /data/openpilot
nano opendbc_repo/opendbc/car/honda/values.py      # or vim, or scp files over
sudo systemctl restart comma                         # restarts the launch script
tmux a                                               # watch it start / see tracebacks
```

- Python-only changes: the restart is quick. `build.py` still runs scons, but it is
  incremental and finishes in seconds when nothing compiled changed.
- C/C++ changes (panda safety, anything with a SConscript): scons recompiles the
  affected parts. A minute to several minutes.
- When something you tried works, commit it on the device (`git commit`) and push to
  your fork, or redo the change on the PC and push from there. Don't leave good work
  only on the device.

### Changing opendbc (the Honda port)

opendbc is a submodule, so it needs two commits:

```bash
# 1. inside the submodule, on its own dev branch
cd opendbc_repo
git checkout dev
# ...edit opendbc/car/honda/*.py...
git commit -am "Honda: describe the change"
git push                      # goes to danielwburch/opendbc branch dev

# 2. in the main repo, record the new submodule commit
cd ..
git add opendbc_repo
git commit -m "bump opendbc"
GIT_LFS_SKIP_PUSH=1 git push
```

The device's updater runs `git submodule update --init --recursive` after fetching,
so it will pick up the new opendbc commit. Over SSH use
`git pull && git submodule update --init --recursive`.

### Pulling MVL's changes later

```bash
git fetch mvl
git checkout sp-honda-202508 && git merge --ff-only mvl/sp-honda-202508   # refresh the mirror
git checkout dev && git merge sp-honda-202508                               # bring into your work
```

(`sp-honda-202508` is frozen so this will rarely change. To move to a newer MVL branch
such as `sp-honda-202607`, fetch it with `git fetch mvl sp-honda-202607` and start a
new working branch from it. Repeat for the matching opendbc branch.)

---

## 6. Debugging on the device

| Want to | Do |
|---------|----|
| See live process output and Python tracebacks | `tmux a` |
| See why the build failed | The screen shows the error; also `tmux a`, or `cat /tmp/launch_log` |
| Check what's installed | `cd /data/openpilot && git log -1 && git submodule status` |
| Force a clean rebuild | `rm -rf /data/scons_cache && sudo reboot` |
| Look at logs from a drive | `/data/media/0/realdata/<route>/` (rlog, qlog, cameras) |
| Inspect CAN traffic | `tools/cabana` on a Linux PC (see section 8), pointed at a recorded route from the device |
| Params (settings) | `python -c "from openpilot.common.params import Params; print(Params().get('UpdaterTargetBranch'))"` |

---

## 7. Windows-specific gotchas in this clone

- **Symlinks are checked out as plain text files.** openpilot uses many symlinks
  (`opendbc` → `opendbc_repo/opendbc`, `tinygrad`, `msgq`, etc.). Windows needs
  Developer Mode to create symlinks, and it is off on this PC, so the clone uses
  `core.symlinks=false`. Git tracks them correctly; the files just aren't followable in
  Explorer. To fix for real: enable Developer Mode (Settings → System → For developers),
  then `git config core.symlinks true && git restore --source=HEAD :/`.
- **Five files are marked `skip-worktree`** (`big_driving_*.onnx`, three `libqpOASES_e`
  libraries). They are symlinks to LFS-tracked files and show as falsely "modified" on
  Windows. They are hidden from `git status` so you don't accidentally commit them. If
  you ever need them visible: `git update-index --no-skip-worktree <path>`.
- **Line endings:** the repo is configured `core.autocrlf=false`, `core.eol=lf`. Keep
  it that way. Shell scripts with CRLF endings break on the device. Set your editor to LF.
- **Git LFS:** the clone was made with `GIT_LFS_SKIP_SMUDGE=1`, so large LFS files
  (driving models `.onnx`, `.so` libraries, fonts, images, sounds) are small pointer
  stubs locally. The device pulls the real ones from sunnypilot's GitLab LFS server.
  If you want them locally: `git lfs pull` (hundreds of MB).
- **Pushing:** the Git LFS pre-push hook tries to upload LFS objects to sunnypilot's
  GitLab over SSH, which you don't have access to, so pushes fail with "Host key
  verification failed". The hook has been **deleted from this clone**
  (`.git/hooks/pre-push`), so plain `git push` works. If it ever comes back (for
  example after `git lfs install` or a fresh clone), either delete it again or push with
  `GIT_LFS_SKIP_PUSH=1 git push` (PowerShell: `$env:GIT_LFS_SKIP_PUSH = 1`).
- **Adding new binary assets** (`.png`, `.svg`, `.wav`, `.ttf`, `.onnx`): `.gitattributes`
  routes those into LFS, which you can't push to. Add a line to `.gitattributes` to opt
  the specific file out, e.g. `selfdrive/assets/my_icon.png -filter -diff -merge`, so it
  is stored as a normal git blob.
- **Disk:** C: has about 21 GB free. The clone is a few GB. Don't `git lfs pull` or set up
  WSL without checking space.

---

## 8. Optional: a Linux dev environment on this PC (WSL2)

For running tests, `tools/replay`, `tools/cabana`, PlotJuggler, or compiling locally,
openpilot wants Ubuntu 24.04. WSL2 is the supported way on Windows:

```powershell
wsl --install -d Ubuntu-24.04
```

Then inside Ubuntu: clone the repo again there (don't use the Windows checkout through
`/mnt/c`, it is slow and symlinks misbehave), run `tools/op.sh setup`, `source
.venv/bin/activate`, `scons -u -j$(nproc)`. Budget ~15 GB of disk.

---

## 9. Housekeeping

### Delete the hundreds of copied MVL branches from your forks

The fork copied every MVL branch. To keep only `dev`, `sp-honda-202508`, `master`:

```bash
for repo in openpilot opendbc; do
  gh api "repos/danielwburch/$repo/branches" --paginate --jq '.[].name' |
  grep -vxE 'dev|sp-honda-202508|master' |
  while read b; do gh api -X DELETE "repos/danielwburch/$repo/git/refs/heads/$b" && echo "deleted $b"; done
done
```

(Run from Git Bash. This only touches your forks; MVL's repos are untouched.)

### GitHub Actions

The fork inherited sunnypilot's CI workflows. The heavy ones are gated to run only in
`sunnypilot/sunnypilot` or `commaai/openpilot`, and the push-triggered ones only fire on
`master`, so pushing to `dev` should not run anything. If you see noisy failing
workflow runs, disable them: github.com/danielwburch/openpilot/settings/actions.

---

## 10. Safety notes

- `opendbc/safety/` (panda safety) and the torque/accel limits in `values.py` are the
  guardrails that keep the car within limits. sunnypilot and openpilot both treat the
  panda safety model as non-negotiable. Read `docs/concepts/safety.md` before touching
  either.
- Test every change in an empty parking lot first, hands on the wheel, foot over the
  brake. A Python traceback in `controlsd` means openpilot simply won't engage, which is
  the safe failure. A wrong tuning value engages fine and drives badly, which is not.
- Keep `sp-honda-202508` as a known-good fallback you can reinstall with
  `smiskol.com/fork/danielwburch/sp-honda-202508`.

---

## Quick reference

```bash
# PC: commit and push
git add -A && git commit -m "msg" && git push

# Device: pull and restart
ssh comma@<ip> "cd /data/openpilot && git pull && git submodule update --init --recursive && sudo reboot"

# Device: quick restart without reboot
sudo systemctl restart comma

# Device: watch output
tmux a
```

Sources used while setting this up: MVL's fork threads on the sunnypilot community
(community.sunnypilot.ai/t/updated-mvl-honda-forks/1805 and the 202605/202607 threads),
sunnypilot's "Installing custom SP forks" and "SSH Installation Method" guides,
sshane/openpilot-installer-generator (smiskol.com/fork), and the commaai openpilot wiki
pages on SSH and the FAQ.
