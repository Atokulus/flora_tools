/* THIS FILE HAS BEEN AUTOGENERATED BY FLORA-TOOLS */

#ifndef LWB_CONSTANTS_H
#define LWB_CONSTANTS_H

#define LWB_SCHEDULE_GRANULARITY %%LWB_SCHEDULE_GRANULARITY%% // %%human_time(LWB_SCHEDULE_GRANULARITY)%%
#define LWB_SYNC_PERIOD %%LWB_SYNC_PERIOD%% // %%human_time(LWB_SYNC_PERIOD)%%

#define LWB_CONTENTION_HEADER_LENGTH %%LWB_CONTENTION_HEADER_LENGTH%%
#define LWB_DATA_HEADER_LENGTH %%LWB_DATA_HEADER_LENGTH%%
#define LWB_MAX_DATA_PAYLOAD %%LWB_MAX_DATA_PAYLOAD%%
#define LWB_SLOT_SCHEDULE_HEADER_LENGTH %%LWB_SLOT_SCHEDULE_HEADER_LENGTH%%
#define LWB_SLOT_SCHEDULE_ITEM_LENGTH %%LWB_SLOT_SCHEDULE_ITEM_LENGTH%%
#define LWB_ROUND_SCHEDULE_ITEM %%LWB_ROUND_SCHEDULE_ITEM%%
#define LWB_ROUND_SCHEDULE_ITEM_COUNT %%LWB_ROUND_SCHEDULE_ITEM_COUNT%%
#define LWB_ROUND_SCHEDULE_LENGTH %%LWB_ROUND_SCHEDULE_LENGTH%%

#define LWB_MOD_COUNT %%LWB_MOD_COUNT%%

extern const uint8_t gloria_default_power_levels[];
extern const uint8_t gloria_retransmission_counts[];
extern const uint8_t gloria_hop_counts[];
extern const uint8_t lwb_modulations[];
extern const int8_t lwb_powers[];
extern const uint32_t lwb_slot_times[][256];
extern const uint32_t lwb_slot_acked_times[][256];

#endif /* LWB_CONSTANTS_H */