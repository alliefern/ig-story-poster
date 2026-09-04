Put your 17 images here, named exactly as below. Uppercase matters: the images are
fetched by URL and GitHub URLs are case-sensitive, so `Quiz_one.jpg` would 404.

| Slide | File |
|---|---|
| Set 1, first then second | `SET_ONE.jpg`, `SET_ONE_A.jpg` |
| Set 2 | `SET_TWO.jpg`, `SET_TWO_A.jpg` |
| Set 3 | `SET_THREE.jpg`, `SET_THREE_A.jpg` |
| Set 4 | `SET_FOUR.jpg`, `SET_FOUR_A.jpg` |
| Set 5 | `SET_FIVE.jpg`, `SET_FIVE_A.jpg` |
| Set 6 | `SET_SIX.jpg`, `SET_SIX_A.jpg` |
| Four-slide quiz, in order | `QUIZ_ONE.jpg`, `QUIZ_TWO.jpg`, `QUIZ_THREE.jpg`, `QUIZ_FOUR.jpg` |
| Standalone quiz | `QUIZ_STANDALONE.jpg` |

## The 12-day loop

| Day | Posts | Day | Posts |
|---|---|---|---|
| 1 | SET_ONE, SET_ONE_A | 7 | SET_FOUR, SET_FOUR_A |
| 2 | QUIZ_ONE to QUIZ_FOUR | 8 | QUIZ_STANDALONE |
| 3 | SET_TWO, SET_TWO_A | 9 | SET_FIVE, SET_FIVE_A |
| 4 | QUIZ_STANDALONE | 10 | QUIZ_ONE to QUIZ_FOUR |
| 5 | SET_THREE, SET_THREE_A | 11 | SET_SIX, SET_SIX_A |
| 6 | QUIZ_ONE to QUIZ_FOUR | 12 | QUIZ_STANDALONE |

Day 13 is Day 1 again. Day 1 is `CYCLE_START_DATE` in `.github/workflows/post-story.yml`.
The loop itself is the `CYCLE` list at the top of `post_story.py`; edit that to change
the order or the slides.

## Image rules

- JPEG only. Meta's publishing API specifies JPEG; treat PNG as unsupported.
- 1080 x 1920 (9:16) is the safe size. Under 8 MB.
- Stories posted through the API are flat images: no quiz sticker, poll, slider, link
  or mention can be added. If a slide is a "quiz", design the question into the image.
- To change a slide, replace the file. Same filename, nothing else to touch.
