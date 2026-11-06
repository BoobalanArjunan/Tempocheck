# tempocheck: real-data check

25 songs, tolerance 4%.

## 1. With the TRUE labels (every FAIL here is a false alarm)

- PASS 21, WARN (half/double) 4, REVIEW 0, FAIL 0, ERROR 0
- **False alarm rate (FAIL): 0.0%**

## 2. With deliberately WRONG labels

- 25 songs given a wrong label (20%+ away): FAIL on **22 (88%)**
- the rest: PASS 1, WARN 2

## 3. Plain tempo accuracy

- Acc1 (within 4%): 84.0%   Acc2 (also half/double/3x/1.5x): 100.0%

For scale: good published trackers reach roughly 60-70% Acc1 and 85-95% Acc2 on hard sets such as GiantSteps. tempocheck is a simple estimator, so lower is plausible; what matters most is section 1 (false alarms).

Songs with a FAIL on the true label (check these by ear, the label may be the thing that is wrong):

- none