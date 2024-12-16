-OSC2MIDI- 

Will need Python 3, install dependacies via command prompt/terminal: pip install python-rtmidi mido python-osc pillow 

REQUIREMENTS FOR WINDOWS : loopMIDI by Tobias Erichsen (creates virtual midi ports)
Launch and make two virtual ports, one for incoming, one for outgoing (+ at bottom left to add new virtual port)

For Mac launch "Audio MIDI Setup". Create two virutal ports, one for incoming, one for outgoing

Ensure Headset/Devices are all on same wifi network
ip will be your ipv4 address (can be found by typing "ip config" in command prompt for Windows, Internet settings for Mac, Android wifi settings)
Port in (default 5550) is from Patch to PC/Mobile, Port out to Patch (default 3330)

The osc addresses are as follows...(X = channel 1-16)

/chXnote 0-127, /chXnvalue 0-1 /chXnoteoff 0-127, /chXnoffvalue 0-1 /chXpitch,-8200 to 8200 (sits at 0), /chX pressure 0-127 /chXcc 0-127, /chXccvalue 0-1

-Patchworld Community Project -
