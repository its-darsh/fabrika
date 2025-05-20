# Fabrika, The Shell

Fabrika is a desktop shell for Wayland, specifically for Hyprland, built on top of [Fabric](https://github.com/Fabric-Development/fabric). It's crafted for high performance without sacrificing rich features, and it even adds a touch of eye-candy.

## Installation

> [!WARNING]
> Fabrika is still experimental. It's intended only for experienced users or those studying the code.
> If you choose to use this configuration, you do so at your own risk.
> Issues related to installation are not going to be addressed.

Although I don't recommend using someone else's configuration without understanding it fully, here's how you can set up Fabrika:

```bash
# clone this repository
git clone https://github.com/its-darsh/fabrika ~/.config/fabric

# enter the cloned repository
cd ~/.config/fabric

# setup a python environment for fabric
python -m venv venv
source venv/bin/activate

# install fabric
pip install git+https://github.com/Fabric-Development/fabric

# kill running notification daemons and status bars
pkill -f "mako|dunst|waybar"

# run the shell
python config.py
```

## Visual Tour

_Coming soon..._
