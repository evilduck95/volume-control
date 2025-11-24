from pulsectl import pulsectl

import windowutils

last_controlled_media = ""


def change_sink_input_volume(pulse: pulsectl.Pulse,
                             sink_input: pulsectl.PulseSinkInputInfo,
                             requested_change: float) -> float:
    current_volume = pulse.volume_get_all_chans(sink_input)
    # Already at maximum, I've elected to ignore over-amplification for now
    if requested_change > 0 and current_volume == 1:
        print('Already at max volume')
        return 0
    # Safety first!
    if current_volume + requested_change > 1:
        actual_change = 1 - current_volume
        print('Volume change: ' + str(requested_change) + ' is too high, restricted to ' + str(actual_change))
    else:
        actual_change = requested_change
    # Make the change and report
    pulse.volume_change_all_chans(sink_input, actual_change)
    updated_volume = pulse.volume_get_all_chans(sink_input)
    print('Changed volume of app by: ' + str(actual_change) +
          '. New Volume: ' + str(updated_volume))
    return updated_volume


def change_active_window_volume(change: float) -> float:
    global last_controlled_media
    active_pid = windowutils.get_active_window_pid()
    with pulsectl.Pulse('volume-manager') as pulse:
        for sink_input in pulse.sink_input_list():
            app_id = sink_input.proplist['application.process.id']
            # print('Next Sink Input: ' + str(app_id))
            if app_id == str(active_pid).strip():
                # print('Found Application: ' + sink_input.proplist['application.name'] +
                #       ', matching PID: ' + str(active_pid))
                media_name = sink_input.proplist['media.name']
                if media_name != last_controlled_media:
                    last_controlled_media = media_name
                    print('Media: ' + media_name)
                return change_sink_input_volume(pulse, sink_input, change)
