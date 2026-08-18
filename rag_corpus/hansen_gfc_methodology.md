# Hansen Global Forest Change: Methodology Notes

## What the lossyear band encodes

The Hansen Global Forest Change dataset (Hansen et al., updated annually) provides a
per-pixel `lossyear` band at 30m resolution. Each pixel holds an integer 0-23, where 0
means no detected loss and values 1-23 encode the calendar year of loss as an offset
from 2000 (e.g. 5 = 2005, 20 = 2020). Forest loss is defined as a stand-replacement
disturbance -- a complete removal of tree canopy cover -- detected via Landsat time
series analysis, not a general land-cover reclassification.

## Coverage and reliability

The dataset covers 2000 to the present and is the most widely-used global forest-loss
product precisely because of this long, consistent time series. Because it targets
tree-canopy loss specifically, it is well suited to "how much forest was lost in this
municipality between year X and year Y" questions, but it does not classify what the
land became afterward (agriculture, settlement, regrowth, etc.) -- that requires a
separate land-cover classification product such as Dynamic World or ESA WorldCover,
both of which have shorter historical coverage (Dynamic World from mid-2015, ESA
WorldCover only for 2021).

## Common pitfalls

Pixel counts must be converted to area using an equal-area projection, not a
geographic (lat/lon) CRS, or loss estimates will be systematically biased depending on
latitude. Analysts should also be aware that "loss" here means canopy removal, not
necessarily deforestation in the land-use sense -- a clear-cut that regrows as forest a
decade later still counts as a loss event in the year it was cut.
