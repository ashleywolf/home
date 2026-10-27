# Universe Schedule

Universe Schedule shows what's on at GitHub Universe 2026 right now and next, lets you star your sessions, and walks Mona to the room on a Fort Mason map.

## Use it

The app opens on a menu with three choices. Press **UP** and **DOWN** to pick
one and **SELECT** to open it:

- **Full catalog**: every session, by time, starting with what's on now and
  next. Press **LEFT** and **RIGHT** to move through 30-minute time slots.
- **My schedule**: only the sessions you starred. **LEFT** and **RIGHT** jump a
  day.
- **Map**: the way from the entrance to your next starred session.

In a list, press **UP** and **DOWN** to pick a session and **SELECT** to open
it. In a session, press **SELECT** to star it and **RIGHT** to see the map.

- **BACK** goes back one step. From a list, it goes to the menu.
- **MENU** jumps to the menu from any screen.
- The white **HOME** circle leaves the app and goes to the badge menu when
  you let go of it. Holding it while the badge restarts opens USB disk mode,
  so tap it instead.

Each session shows its time, room, building and floor, type, speakers, and a
**POPULAR** tag when the room fills up fast, so arrive early.

## Time to go

Ten minutes before one of your starred sessions starts, the four case lights
breathe and a yellow **GO NOW** banner names the session and building. Press
**SELECT** to open the map to that session, or any other button to quiet the
lights. The app has to be open for this to work.

## Map

The map is a simple, not-to-scale plan of Fort Mason. It always starts at the
**Marina Blvd entrance** (marked **START**) and draws a green line to the
session's building. Mona walks the line so you can see the way.

The bar at the bottom names the room, the walking time, and one numbered step
at a time, from the entrance to the building and then to the room. The steps
change every few seconds; press **LEFT** and **RIGHT** to flip through them
yourself. Press **SELECT** to zoom out to the whole map and again to zoom back
in. Off-site parties and venues show their address instead of a route.

The map is a fixed guide, not live tracking. It doesn't know where you are.

## Clock and Wi-Fi

The schedule is built into the app and works fully offline. Times are Pacific
time.

When the app opens, it sets its clock over Wi-Fi if `WIFI_SSID` and
`WIFI_PASSWORD` are set in the Settings app. Without Wi-Fi it uses the badge
clock. If the badge clock isn't set either, a yellow **PREVIEW** tag shows and
the app starts on Wednesday, October 28, 8:30 AM, so you can try it anywhere.

## Test day

Hold **MENU** for two seconds to turn on a **TEST DAY**: the app pretends it's
Wednesday, October 28, 10:20 AM, so you can see the schedule, map, and
**GO NOW** alert before the event. Hold **MENU** again to go back to the real
clock.

If the app folder also has an optional, private venue file (`sfoffice.py`),
holding **MENU** switches to that venue's map and a practice schedule on the
real clock instead. That file isn't part of this repository.

## Your data

Stars and the clock correction are saved to `/state/universe_schedule.json`.
Nothing leaves the badge. The registration portal has no export, so star your
sessions on the badge.

## Data

`assets/sessions.json` is a compact copy of the public Universe 2026 session
catalog: id, start and end minutes from October 26, 2026 at midnight Pacific,
title, type, track, room, building or floor, speakers, and a popular flag.
Building positions in `fortmason.py` are approximate.
