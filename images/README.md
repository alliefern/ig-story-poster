Put your 14 images here, named exactly:

| Weekday | First image (rotates) | Second image (that day's companion) |
|---|---|---|
| Monday | `SET_ONE.jpg` | `SET_ONE_A.jpg` |
| Tuesday | `SET_TWO.jpg` | `SET_TWO_A.jpg` |
| Wednesday | `SET_THREE.jpg` | `SET_THREE_A.jpg` |
| Thursday | `SET_FOUR.jpg` | `SET_FOUR_A.jpg` |
| Friday | `SET_FIVE.jpg` | `SET_FIVE_A.jpg` |
| Saturday | `SET_SIX.jpg` | `SET_SIX_A.jpg` |
| Sunday | `SET_SEVEN.jpg` | `SET_SEVEN_A.jpg` |

Want the second image to look identical every day? Just upload the same picture as
all seven `_A` files — the script doesn't know or care that they're duplicates.

.jpg or .png both work — if you use .png, update the `day_filename` /
`companion_filename` lines in `post_story.py` to say `.png` instead.
