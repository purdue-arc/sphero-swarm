# An Integrated Multi-Robot Platform for Embodied Visualization of Step-Growth Polymerization

**[Author 1], [Author 2], [Author 3], [Author 4], [additional authors]**  
**[Department or organization], Purdue University, West Lafayette, Indiana, USA**  
**[Partner organization, if applicable]**  
**Corresponding author:** [name and email]

> **Draft status:** Development draft for ICAR 2027. Text in square brackets must be completed or verified before submission. Quantitative results have deliberately not been invented. Transfer the final manuscript to the official IEEE conference template; Google Docs is suitable for collaborative drafting, but not as the submitted layout.

## Abstract

Dynamic chemical processes are commonly communicated through symbolic notation, static molecular models, or screen-based animation. These representations do not physically realize the collective motion through which larger structures emerge from local interactions. This paper presents an integrated multi-robot platform that maps a simplified case of step-growth polymerization onto the motion and visual state of Sphero BOLT robots. Each robot represents a monomer with a configurable head or tail trait. A centralized lattice-based planner applies trait-dependent bonding rules, maintains bonded groups, and selects collision-aware translations and rotations. An overhead perception subsystem combines AprilTag-based arena rectification with a custom YOLOv8 detector and BoT-SORT tracking to estimate robot positions. A multithreaded Bluetooth Low Energy control service converts planned state transitions into synchronized LED, heading, and rolling commands, while an Electron/React interface exposes configuration, system state, camera telemetry, and simulation controls. The current prototype has demonstrated an integrated physical process with six robots, simulation with eight robots, and simultaneous Bluetooth connection with twelve robots. We evaluate the platform in terms of [formation correctness], [position error], [tracking consistency], [command latency], and [connection scaling]. Across [N] integrated trials, the system achieved [RESULTS TO BE INSERTED]. These results characterize the opportunities and present limitations of using commodity mobile robots as a reconfigurable physical medium for visualizing rule-governed chemical assembly.

**Index Terms—** multi-robot systems, embodied visualization, robotic displays, computer vision, step-growth polymerization, educational robotics

## I. Introduction

Many chemical processes require learners and observers to reason simultaneously about microscopic entities, local interaction rules, and structures that emerge over time. Conventional molecular kits provide physicality but require manual manipulation and generally represent static structures. Screen-based simulations provide motion and rapid reconfiguration but confine the representation to a display. Mobile robots offer a third possibility: each robot can act as a persistent physical element whose position, motion, and visual state are controlled computationally.

Prior work has established the potential of robots and tangible interfaces as dynamic representations. Batra, Klingner, and Correll used a robot swarm to simulate atoms and augmented reality to expose internal state and molecular bonds [1]. Li, Suzuki, and Nakagaki introduced Physica, in which tabletop robots embody objects in interactive physics simulations [2]. Earlier tangible chemistry systems enabled users to construct and manipulate molecular representations through physical interfaces [3]. These projects motivate embodied scientific visualization, but they also expose a practical systems problem: a physical display must consistently translate abstract model states into coordinated motion despite actuation error, communication limits, visual ambiguity, and interactions among already assembled groups.

We present a camera-guided multi-robot platform developed as the software foundation for a planned public science exhibit. The long-term exhibit will allow a user to select a natural or chemical process through an application, after which a set of mobile robots will physically display the process. The present paper does not evaluate visitor learning or the final exhibit enclosure. Instead, it focuses on the current robotics contribution: the integration of a rule-based assembly model, bonded-group motion planning, overhead state estimation, concurrent Bluetooth control, and an operator interface.

The platform uses a simplified head-tail-tail bonding case inspired by step-growth polymerization. Robots move on a discrete lattice, form groups when compatible monomers become adjacent, and subsequently translate or rotate while preserving group membership. LED colors communicate monomer traits and completed groups. Unlike decentralized swarm-control approaches [4], the current prototype uses centralized state and planning. We therefore use the term multi-robot display to describe the implemented control structure and reserve decentralized swarm control for future work.

This paper makes four contributions:

1. A configurable representation that maps monomer traits, bonding eligibility, group membership, and completion state onto robot position and LED color.
2. A lattice-based planner that supports trait-constrained bonding, collision-aware translation, edge-conflict avoidance, and rotation of bonded robot groups.
3. An integrated perception-planning-control architecture combining arena rectification, learned object detection, multi-object tracking, synchronized Bluetooth actuation, and a live operator interface.
4. A prototype evaluation spanning algorithmic correctness, perception accuracy, motion execution, communication scaling, and six-robot end-to-end formation trials.

The evaluation separates simulated scale, connection scale, and end-to-end physical scale. This distinction prevents connectivity with twelve robots from being conflated with a twelve-robot formation demonstration.

## II. Related Work

### A. Robot Swarms and Multi-Robot Coordination

Swarm robotics traditionally emphasizes simple local interactions, decentralized control, robustness, and scalability [4]. The platform presented here shares the visual and behavioral characteristics of a robotic swarm but currently relies on centralized perception and planning. Its primary technical concerns are therefore multirobot state estimation, concurrent actuation, collision avoidance, and preservation of connected groups.

Multi-robot systems frequently decompose operation into perception, planning, and control. In physical systems, however, errors accumulate across these boundaries. The planner reasons about discrete positions, robots execute continuous motion, and perception must recover a state suitable for subsequent decisions. This work studies that integration in the specific setting of an actuated scientific display.

### B. Robots as Dynamic Physical Representations

Batra et al. demonstrated a closely related chemistry application in which robots represented atoms and augmented reality visualized internal state and topological bonds [1]. Their primary contribution was an augmented-reality registration framework and a distributed graph-coloring formulation for visually distinguishing groups. Our work instead emphasizes an integrated external-perception and control pipeline, group-preserving lattice motion, and operation with commercially available spherical robots.

Physica used Sony Toio robots as actuated tangible elements coupled to a two-dimensional physics engine [2]. Its examples included gravity, springs, damping, and molecular motion. Our system differs in its use of explicit trait-dependent bonding rules, persistent bonded groups, group rotations, camera-derived state feedback, and Bluetooth-controlled spherical robots.

Tangible interfaces have also been explored for chemistry education. Fjeld et al. compared an augmented tangible chemistry interface with conventional ball-and-stick models and subsequently redesigned its graphical controls [3]. The present work does not measure learning outcomes. It instead contributes and evaluates the robotics infrastructure required to produce a dynamic physical representation.

### C. Vision-Based Robot State Estimation

The perception subsystem combines fiducial-based arena calibration with learned object detection and tracking. AprilTag provides robust visual fiducials suitable for pose estimation and controlled experimental calibration [5]. A custom Ultralytics YOLOv8 model detects spherical robots in the rectified scene [6]. BoT-SORT maintains track identities using motion and appearance associations [7]. These components are integrated with an application-specific display-ID layer and a coordinate transformation from image space to the planner lattice.

## III. System Overview

The platform contains five interacting layers: process representation, motion planning, perception, actuation, and operator interaction. Fig. 1 should show the complete information flow.

**[FIGURE 1 ABOUT HERE]**  
**Fig. 1.** System architecture. A process configuration initializes monomer traits and lattice positions. The planner updates bonds and selects group motions. Commands are sent to the Bluetooth control service, which actuates the Sphero BOLT robots. An overhead OAK-D camera provides frames to the rectification, detection, and tracking pipeline. Estimated coordinates return to the planner and are also streamed to the operator interface.

The current prototype runs the primary services on a local computer. The perception service publishes robot coordinates through a ZeroMQ request-reply interface. The algorithm driver publishes state and accepts user commands through WebSockets. A separate control service receives batches of robot instructions over a local TCP connection and communicates with the robots over Bluetooth Low Energy. The operator interface is implemented with Electron and React.

The architecture intentionally separates simulation from physical actuation. The same planner state can drive the graphical simulation alone or can additionally be translated into robot commands. This allows algorithm development without requiring all robots to be connected.

## IV. Embodied Polymerization Model

### A. State Representation

Let the arena be a discrete lattice

G = {0, ..., W - 1} x {0, ..., H - 1}.

Each robot i has state

s_i = (p_i, p_i*, tau_i, g_i, c_i, h_i),

where p_i is its current lattice position, p_i* is its next target, tau_i is its monomer trait, g_i is its bonded-group identifier, c_i is its LED color, and h_i is its heading. In the present case study, tau_i is either head or tail. Head robots are initialized as red and tail robots as blue. Robots in a completed group are displayed as green.

A bonded group B_k contains one or more robots sharing group identifier k. Each group stores its size, center robot, axis-aligned bounding box, and currently available moves. Group membership persists after bonding.

### B. Bonding Rules

Two robots are spatially eligible to bond when their positions are adjacent in the eight-connected neighborhood. Spatial eligibility alone is insufficient. The current process imposes the following trait rules:

1. A bonded group may contain at most one head robot.
2. Initial bonding must occur between a singleton head and a tail; two unbonded tail-only groups cannot initiate a structure.
3. Tail-tail bonding is permitted only when exactly one of the two candidate groups already contains a head.
4. A head may bond only while its group contains that head alone.
5. The combined group may not exceed a configurable maximum number of monomers.

When two compatible groups meet, all robots in the second group are reassigned to the first group. The group center and bounding box are recalculated. When the configured maximum size is reached, each group member changes to the completion color.

This rule set is a deliberately simplified embodied analogy of one head-tail-tail step-growth case. It does not model bond energies, reaction kinetics, molecular geometry, reversible reactions, three-dimensional structure, or conservation of chemical species. The system represents rule-governed assembly rather than molecular-scale dynamics.

**[FIGURE 2 ABOUT HERE]**  
**Fig. 2.** Embodied representation. (a) Head and tail traits and their LED colors. (b) Valid initial head-tail bond. (c) Invalid head-head and uninitiated tail-tail bonds. (d) Valid tail extension of a head-containing group. (e) Completed three-monomer group shown in green.

## V. Bonded-Group Motion Planning

### A. Candidate Motions

At each discrete step, the planner updates bonds and processes every nonempty group. Candidate group actions consist of eight one-cell translations and, for groups containing more than one robot, clockwise or counterclockwise 90-degree rotation. Candidate actions are sampled without replacement until a valid action is found. If none is valid, the group remains stationary.

The current policy is stochastic rather than goal directed. Its purpose is to produce repeated encounters under collision and group-preservation constraints. A deterministic seed is required for reproducible simulation experiments.

### B. Translation Validation

For a translation d = (delta_x, delta_y), every robot in the group proposes

p_i* = p_i + d.

The move is valid only if all targets lie within the configured arena margin and do not conflict with cells reserved by previously processed groups. The planner checks both the current grid and the next grid. A doubled-resolution edge grid reserves the traversed edge between source and destination cells, preventing two robots from passing through the same edge during one step.

### C. Group Rotation

For a bonded group, the robot closest to the arithmetic mean of member coordinates is chosen as the discrete center. Clockwise rotation maps an offset (x, y) to (y, -x), while counterclockwise rotation maps it to (-y, x). Before accepting a rotation, the planner rotates the group's bounding box and rejects the motion if the swept region is outside the arena or occupied by another group.

The bounding-box test is conservative: it may reject a geometrically feasible motion if the enclosing box is occupied even when the exact robot trajectories would remain separated. This choice favors simple collision prevention over motion completeness.

### D. Conversion to Physical Commands

After a valid transition is selected, the driver computes a desired heading adjustment and speed for each robot. The current implementation scales translational speed with the distance between the measured and target positions. Commands are grouped into three synchronized phases: LED update, heading update, and roll. The control service acknowledges each batch before the next phase is sent.

Prior to final experiments, the angle computation and moving-versus-stationary branch must be verified with unit tests. The final paper should state the corrected formulation, units, and saturation limits used in the submitted experiments.

## VI. Perception and Control

### A. Arena Rectification

An overhead OAK-D camera observes the arena. Four AprilTags near its corners define a quadrilateral corresponding to the active surface. The detector extracts selected tag corners and computes a perspective transformation into a 500 x 500 pixel top-down frame. To reduce processing overhead, tag detection is performed every five frames and the most recent homography is reused between detections.

### B. Robot Detection and Tracking

A custom YOLOv8 model detects Sphero robots in each rectified frame. BoT-SORT associates detections across frames. On initialization, tracker identities are assigned display identifiers using a deterministic spatial ordering. When a track is lost and a new tracker identity appears, the current implementation preferentially assigns the new track to the nearest lost display identifier.

The perception pipeline uses bounded queues and discards stale frames when processing falls behind acquisition. This design prioritizes recent state over complete frame processing, which is appropriate for feedback but must be reflected in latency measurements.

Detected centers are converted from pixels to continuous grid coordinates using the measured arena dimensions and the physical distance associated with one nominal lattice move. Coordinates are provided as JSON when the planner requests the current state.

The display-ID layer does not inherently prove correspondence between a visual track and a Bluetooth device. For the submitted experiments, the initialization procedure must establish and document this mapping, and identity-switch metrics must be computed relative to manually annotated or otherwise verified ground truth.

### C. Concurrent Bluetooth Control

The control subsystem uses the `spherov2` Python library [8]. Discovery and connection operations are parallelized across robot-specific threads. Command batches contain one optional instruction per connected robot. The control server launches a thread for each robot so that LED, heading, rolling, and waiting actions execute concurrently.

Roll commands are bounded by a configured duration and terminate with an explicit stop command. Turn commands incrementally modify heading over a specified duration. If the client connection terminates, the server queues stop or termination instructions for the connected robots. The prototype currently uses a single host and local sockets; distributed Bluetooth controllers are future work and are not evaluated in this paper.

### D. Operator Interface

The Electron/React interface provides four functions relevant to development and evaluation: configuration of arena and robot parameters, Bluetooth connection management, visualization of the camera and perception telemetry, and display of the algorithm state. Operators can enable physical controls, pause or resume execution, select color behavior, and manually specify a robot path while the simulation is paused.

The current GUI is an engineering interface rather than the final public application. The planned exhibit interface will allow visitors to select a process without exposing low-level configuration.

## VII. Experimental Evaluation

### A. Research Questions

The evaluation addresses five questions:

RQ1: Does the planner preserve bonding and collision invariants across randomized simulations?

RQ2: How accurately and consistently does the perception system estimate robot position and identity?

RQ3: How accurately do robots execute individual translations and bonded-group motions?

RQ4: Does camera-derived correction reduce endpoint or formation error relative to open-loop execution?

RQ5: How do Bluetooth connection time, connection success, and command latency change with robot count?

### B. Apparatus and Reproducibility

Experiments were performed using [NUMBER AND MODEL OF COMPUTER], [OPERATING SYSTEM], [CPU], [GPU OR ACCELERATOR], an [OAK-D MODEL] camera mounted [HEIGHT] above an arena measuring [DIMENSIONS], and up to twelve Sphero BOLT robots. The active lattice was [W x H], with nominal spacing of [DISTANCE]. Perception used model file [MODEL NAME/HASH], image size [VALUE], and confidence threshold [VALUE]. Motion parameters were [ROLL SPEED], [DIAGONAL SPEED], [ROLL DURATION], and [TURN DURATION].

The software version used for all experiments is archived at [ANONYMOUS REPOSITORY OR DOI] with commit [HASH]. Each trial records the configuration, random seed, timestamps, planned states, measured positions, commands, connection events, detections, and outcome. Raw data and analysis scripts will be released at [REPOSITORY].

### C. Simulation Correctness

Run at least [1,000] seeded simulations at each selected combination of robot count, grid size, trait distribution, and maximum group size. Validate after every transition that:

- each robot occupies exactly one in-bounds cell;
- no cell contains more than one robot;
- no two trajectories claim the same opposing edge;
- all group members share the same group identifier;
- each group contains at most one head;
- no group exceeds the configured maximum size; and
- completed groups use the expected state color.

**[TABLE I ABOUT HERE]**

**Table I. Simulation correctness and computational performance**

| Robots | Grid | Trials | State transitions | Invariant violations | Completion rate | Median step time |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 4 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 6 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 8 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| [larger simulated count] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

Results: Across [N] transitions, the planner produced [N] invariant violations. Completion rate [increased/decreased] from [VALUE] at [CONDITION] to [VALUE] at [CONDITION]. Median planning time was [VALUE] ms at eight robots and [VALUE] ms at [LARGER COUNT]. [Interpret only after measurements exist.]

### D. Perception Accuracy and Identity Consistency

Construct an annotated data set spanning [robot counts], [lighting conditions], stationary and moving robots, partial occlusion, arena edges, and robot crossings. Ground-truth centers should be marked in the rectified frame or obtained from an independent fiducial procedure. Report precision, recall, center error, grid-cell accuracy, ID switches, IDF1, and processed frame rate. Separate detector performance from tracker performance.

**[TABLE II ABOUT HERE]**

**Table II. Perception performance by robot count**

| Robots | Frames | Precision | Recall | Median center error | 95th percentile error | ID switches | FPS |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 4 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 6 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| 8 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

Results: The detector achieved [VALUE] recall and a median center error of [VALUE] [pixels/mm/grid units] with six robots. Tracking produced [VALUE] identity switches over [VALUE] robot-seconds. The principal failure modes were [OCCLUSION/COLOR CHANGE/BOUNDARY/LIGHTING].

### E. Motion and Feedback Accuracy

Evaluate axial moves, diagonal moves, turns, and bonded-group rotations. For each action type, use at least [30] repeated trials distributed across arena locations and robots. Measure Euclidean endpoint error, angular error where applicable, action duration, collision incidence, and successful arrival within a predefined tolerance.

To evaluate feedback, use matched initial conditions for open-loop and perception-informed control. Define the primary endpoint and statistical comparison before running the experiment. Report individual observations or distribution plots, not only means.

**[FIGURE 3 ABOUT HERE]**  
**Fig. 3.** Motion accuracy. Endpoint-error distributions for axial translation, diagonal translation, and bonded-group rotation. The feedback comparison uses matched initial conditions and identical target sequences.

Results: Feedback [reduced/did not significantly reduce] median endpoint error from [VALUE] to [VALUE], corresponding to [VALUE]% change. Formation success changed from [VALUE] to [VALUE]. The most common execution failure was [DESCRIPTION].

### F. Bluetooth Connection and Command Scaling

For robot counts 1, 2, 4, 6, 8, 10, and 12, repeat discovery and connection [N] times. Measure the number discovered, number connected, time to first connection, time to complete the connection attempt, and command acknowledgement latency. The twelve-robot condition evaluates connectivity only unless a twelve-robot physical process is separately completed.

**[FIGURE 4 ABOUT HERE]**  
**Fig. 4.** Bluetooth scaling. Connection success, total connection time, and command latency as a function of requested robot count. Points show individual trials; lines show medians with [confidence intervals/interquartile ranges].

Results: The system connected [VALUE] of [VALUE] requested robots across [N] trials. At twelve requested robots, the median connected count was [VALUE], and median connection time was [VALUE] s. Command acknowledgement latency was [VALUE] ms for six connected robots and [VALUE] ms for twelve.

### G. Integrated Six-Robot Demonstration

The full pipeline was evaluated with six robots across [N] initial configurations. A trial was successful if [DEFINE BEFORE TESTING: all intended groups reached the maximum size, all bonds satisfied trait rules, no unresolved collision occurred, and completion occurred within a specified number of steps or time]. Report connection failures and perception failures separately from planner failures.

**[FIGURE 5 ABOUT HERE]**  
**Fig. 5.** Representative six-robot physical trial. Rows show the rectified camera view, estimated lattice state, and planned group state at selected times. Head robots are red, tail robots are blue, and completed groups are green.

**[TABLE III ABOUT HERE]**

**Table III. End-to-end six-robot results**

| Initial configuration | Trials | Successful formations | Median completion time | Collisions | Tracking failures | Control failures |
|---|---:|---:|---:|---:|---:|---:|
| [A] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| [B] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| [C] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

Results: The system completed [VALUE] of [VALUE] trials. Successful trials required a median of [VALUE] planning steps and [VALUE] s. Of the unsuccessful trials, [VALUE] were attributable to perception, [VALUE] to Bluetooth or actuation, [VALUE] to planner behavior, and [VALUE] to [OTHER].

## VIII. Discussion

The prototype demonstrates how a chemical assembly rule set can be connected to a physical multi-robot pipeline. Its primary value is not chemical fidelity but the preservation of an explicit mapping from abstract traits and adjacency constraints to visible motion, grouping, and color. The same architecture separates process state from robot actuation, allowing the planner to operate in simulation or with physical robots.

The bonded-group abstraction is useful because assembly changes the unit of motion. Before bonding, each robot moves independently; afterward, the group must translate or rotate without losing its topology. The current lattice representation makes these constraints tractable and provides clear collision invariants. It also introduces limitations: motion is quantized, rotation uses a conservative bounding box, and stochastic action selection may be inefficient.

Perception is a central source of both capability and uncertainty. Arena rectification allows the planner to operate in a stable coordinate system, while learned detection avoids attaching a fiducial marker to each spherical robot. However, visually similar robots make identity recovery difficult after occlusion. LED changes used to communicate chemical state may also modify robot appearance. Quantifying these effects is necessary to distinguish successful detection from reliable robot-specific feedback.

Bluetooth connectivity constitutes a separate scaling limit. Parallel connection threads reduce setup time, but the current system uses one host and one Bluetooth subsystem. The ability to establish twelve simultaneous connections does not establish that twelve robots can execute synchronized formations. A distributed architecture with per-controller robot rosters may ultimately be required, but it is outside the scope of this prototype evaluation.

The platform is motivated by an interactive science-center display, but the present results do not establish educational benefit or unattended exhibit reliability. The current Electron interface is intended for configuration and debugging. A later visitor-facing application will expose a curated set of process selections while hiding low-level controls. Learning outcomes and long-duration exhibit operation should be studied only after that interaction and enclosure are complete.

## IX. Limitations and Future Work

First, the polymerization model is a simplified rule-based analogy rather than a predictive chemical simulation. Future work should validate each representation with chemistry domain experts and distinguish general assembly rules from reaction-specific rules.

Second, the planner is centralized and stochastic. It does not provide optimality or expected-time guarantees, and the present implementation should not be described as decentralized swarm intelligence. Future work could compare goal-directed, sampling-based, and decentralized policies.

Third, the visual tracker assigns display identities rather than directly reading each robot's Bluetooth identity. Robot-specific closed-loop correction therefore depends on a controlled initialization procedure and recovery heuristic.

Fourth, physical validation is currently limited to six robots, while eight-robot operation has been demonstrated only in simulation and twelve-robot operation only at the connection layer. Future work will extend end-to-end validation after the network and control architecture are distributed.

Finally, the exhibit enclosure, charging system, public application, visitor evaluation, and visualization of natural processes remain future work. They are motivating applications rather than contributions evaluated in this paper.

## X. Conclusion

This paper presented an integrated multi-robot platform for embodied visualization of a simplified step-growth polymerization process. The system maps monomer traits and bonding rules onto robot motion and LED state, preserves bonded groups through collision-aware lattice translations and rotations, estimates robot state using an overhead camera, and actuates multiple Sphero BOLT robots through concurrent Bluetooth commands. The prototype establishes a software foundation for a reconfigurable physical display while exposing measurable challenges in identity tracking, continuous-to-discrete state conversion, motion accuracy, and wireless scaling. Quantitative evaluation across simulation, subsystem benchmarks, and six-robot physical trials provides [FINAL ONE-SENTENCE RESULT AFTER DATA COLLECTION].

## Acknowledgment

The authors thank [ADVISORS], the Purdue Autonomous Robotics Club, [CHEMISTRY COLLABORATORS], and [SCIENCE-CENTER PARTNER] for their contributions and support. This work was supported by [FUNDING SOURCES].

**AI-use disclosure to review before submission:** IEEE currently requires disclosure of AI-generated manuscript content. If text from this development draft remains in the submitted manuscript, add a disclosure identifying OpenAI Codex, the affected sections, and how it was used. All authors must independently verify the technical content, references, and claims.

## References

[1] S. Batra, J. Klingner, and N. Correll, “Augmented reality for human-swarm interaction in a swarm-robotic chemistry simulation,” *Artificial Life and Robotics*, vol. 27, pp. 407–415, 2022, doi: 10.1007/s10015-022-00763-w.

[2] J. Li, R. Suzuki, and K. Nakagaki, “Physica: Interactive tangible physics simulation based on tabletop mobile robots towards explorable physics education,” in *Proc. ACM Designing Interactive Systems Conf. (DIS)*, 2023, pp. 1485–1499, doi: 10.1145/3563657.3596037.

[3] M. Fjeld, J. Fredriksson, M. Ejdestig, F. Duca, K. Bötschi, B. Voegtli, and P. Juchli, “Tangible user interface for chemistry education: Comparative evaluation and re-design,” in *CHI ’07 Extended Abstracts on Human Factors in Computing Systems*, 2007, doi: 10.1145/1240624.1240745.

[4] M. Brambilla, E. Ferrante, M. Birattari, and M. Dorigo, “Swarm robotics: A review from the swarm engineering perspective,” *Swarm Intelligence*, vol. 7, no. 1, pp. 1–41, 2013, doi: 10.1007/s11721-012-0075-2.

[5] E. Olson, “AprilTag: A robust and flexible visual fiducial system,” in *Proc. IEEE Int. Conf. Robotics and Automation (ICRA)*, 2011, pp. 3400–3407, doi: 10.1109/ICRA.2011.5979561.

[6] G. Jocher, A. Chaurasia, and J. Qiu, “Ultralytics YOLOv8,” software, version 8.0.0, 2023. [Online]. Available: https://github.com/ultralytics/ultralytics

[7] N. Aharon, R. Orfaig, and B.-Z. Bobrovsky, “BoT-SORT: Robust associations multi-pedestrian tracking,” arXiv:2206.14651, 2022, doi: 10.48550/arXiv.2206.14651.

[8] A. Grandi, “SpheroV2 Python API documentation,” release 0.12. [Online]. Available: https://spherov2.readthedocs.io/

**[Add references on multi-robot collision avoidance, centralized multirobot planning, embodied scientific visualization, step-growth polymerization, and any prior Sphero-based research actually discussed in the final manuscript. Verify every citation against the publisher record before submission.]**

## Author Worklist Before Submission

1. Confirm the author list, author order, affiliations, corresponding author, funding, and acknowledgments.
2. Ask a chemistry collaborator to verify the head-tail-tail interpretation and supply an appropriate polymer chemistry citation.
3. Correct and unit-test heading correction, display-ID allocation, rotation bounds, and coordinate conversion before freezing the experimental commit.
4. Define success, collision, identity switch, and endpoint tolerance before collecting results.
5. Run and archive all simulation, perception, motion, Bluetooth, feedback-ablation, and six-robot trials.
6. Replace every bracketed placeholder; remove all drafting notes.
7. Create five publication-quality figures and a one-minute demonstration video.
8. Shorten the manuscript to the ICAR page limit after moving it into the official IEEE template.
9. Verify the 2027 call for papers when its full author instructions are published.
10. Perform a complete reference audit and plagiarism/self-overlap check.
11. Add the required IEEE AI-use disclosure if AI-generated language remains.
