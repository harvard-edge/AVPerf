# AV Benchmarks
![Scenes](https://github.com/harvard-edge/AVPerf/blob/main/images/Scenes.png)

This project aims to create an AV benchmarks suite to evaluate AV system. We adopt the state-of-the-art Apollo AV stack and create three safety-critical scenes to conduct end-to-end analysis. We collect AV metrics, including collision, minimum distance, and safe end-to-end processing rate to evaluate the AV system on different scenes.

There are three safety-critical scenes listed below:
- cut-in
- cut-out
- vehicle following

Please reference to [SVL documentation](https://www.svlsimulator.com/docs/system-under-test/apollo-master-instructions/) to run Apollo AV stack with SVL simulator. For Apollo AV stack, please clone the latest version of Apollo and replace the `modules` folder with the `apollo_modified_modules` provided in this repository.

To run a single scenario
```
python safety-critical/$SCENE $FPS $INDEX (e.g., python safety-critical/cut-in.py 5 1)
```
To run multiple scenarios
```
cd scripts
./run.sh
```
Inside `run.sh`, user can modify `FPS_start` and `FPS_end` to change the range of sweeping FPS, and change `iteration` for the experiment runs for each FPS.
