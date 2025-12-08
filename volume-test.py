from pulsectl import pulsectl

with pulsectl.Pulse('system-volume-manager') as pulse:
    # Get Current Output Device
    default_sink = pulse.sink_default_get()
    current_volume = pulse.volume_get_all_chans(default_sink)
    pulse.volume_change_all_chans(default_sink, -.1)
    print(f'Changed volume by: {.01}')

