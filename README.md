<img width="163" height="31" alt="logo - Copy" src="https://github.com/user-attachments/assets/b0f8cc0b-01e2-41e9-9600-cdc145be2491" />


# What is a ShugrPi®?
The 'Stormwrecker Handheld Undersized Gaming Raspberry Pi' or 'ShugrPi' is pretty much exactly as it sounds. It is a Raspberry Pi 4b that runs a custom 'OS' (made in Pygame) that you can launch you games from (also made in Pygame).


## How does the OS work?
The OS is really a Pygame emulator. The emulator reads the `/game` folder, scans it for Pygame projects, and displays the available games. The Pygame projects are formatted exactly like they normally would be, having a master folder and all of its assets contained inside of that master folder. The only difference is that you do not need a `/venv` or `/.idea` folder. Launching a game via emulator executes the `main.py` file inside of the project, consequently opening a new window, etc. While the game is active, the emulator gets 'paused' until the game is exited. A Pygame project not containing a `main.py` file **will not be recognized by the emulator**, so be sure to format your projects correctly. Use relative paths to keep your game together. For bonus, if you include a `thumbnail.png` file in your Pygame project, it will get displayed in the UI.


## How do I turn my Raspberry Pi 4 into a ShugrPi®?
Easy... Just read the handy .pdf file I put in this repository.

Hardware-wise, I don't provide a list of components that are required for this project as I myself am unsure what you'll need exactly. But I can say you'd generally need:
* A Raspberry Pi 4b (with 4 GB of RAM)
* A Power Management Board
* A LiPo battery or some other power source
* 3D-printed housing for all the components
* 800x480 HDMI Display (with sound output)
* Buttons, Wires, and other technical goodies
* A USB-keyboard for development (optional)
* Games (make sure to account for limited availability as far as user input goes)
  
The emulator runs a 'translator' in a thread that converts GPIO input into keyboard input, so no worries there.


## Screenshots
<img width="477" height="268" alt="image" src="https://github.com/user-attachments/assets/1bd94c81-a854-4be3-9f94-44d63abeabc1" />

I just inserted some dummy games for a test. The game/project on the left does not have a thumbnail available, thus the error image.
Each thumbnail has `.set_colorkey(WHITE)` called on it, so keep that in mind when crafting one.
The banner on the bottom displays the corrected name of the master folder of the selected project (e.g. `Flappy_bird` -> `Flappy Bird`).
The banner on the top displays the time (24-hour format) and the status of your internet connection (based on whether your Ipv4 matches `127.0.0.1` or not).
The time is based off of your Pi's time, and the wifi status updates every three seconds. Also, displayed under the top banner is your framerate.
This number should always stay around 60.


## Notes
* This is currently a work in progress.
* The .pdf may not be entirely accurate code-wise, as I haven't tested everything out yet, but in theory, it **should** work.
* Because the 'ShugrPi' is really *my* version of the setup, I made everything generic in here, so you don't have to worry about copyright infringement.
* Feel free to personalize anything.
* This is not a substitute for RetroPie, so if you're looking for something more versatile, go that route instead.
* This project was entirely made to see how a gaming console that runs (and runs on) Pygame would work out.
