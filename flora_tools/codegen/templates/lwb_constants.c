/* THIS FILE HAS BEEN AUTOGENERATED BY FLORA-TOOLS */

#include <stdint.h>

#include "lwb_constants.h"

uint8_t gloria_default_power_levels = {<%-for power in gloria_default_power_levels %>%%power%%,<%- endfor %>}; // see radio_powers
uint8_t gloria_retransmission_counts = {<%-for count in gloria_retransmission_counts %>%%count%%,<%- endfor %>};
uint8_t gloria_hop_counts = {<%-for count in gloria_hop_counts %>%%count%%,<%- endfor %>};

uint8_t radio_modulations = {<%-for modulation in radio_modulations %>%%modulation%%,<%- endfor %>}; // {<%-for modulation in radio_modulations %>%%modulation_name(modulation)%%,<%- endfor %>}
uint8_t radio_powers = {<%-for power in radio_powers %>%%power%%,<%- endfor %>}; // dBm