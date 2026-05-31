## Overview

The lock release timing must be observed carefully. Lock release timing
occurs at the boundary of the critical section. The lock release timing
measurement is taken before the scheduler tick. Inaccurate lock release
timing reports lead to false positives in the profiler output.
