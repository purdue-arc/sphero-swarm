export interface PerceptionConfig {
  inputSource: "webcam" | "oakd" | "video";
  videoPath?: string;
  model: string;
  conf: number;
  imgsz: number;
  grid: boolean;
  locked: boolean;
  latency: boolean;
}

export interface SpheroConstants {
  MARGIN: number;
  DIRECTIONS: number;
  ALL_DIRECTIONS: number[];
  position_change: {
    [key: string]: [number, number];
  };
  N_SPHEROS: number;
  GRID_WIDTH: number;
  GRID_HEIGHT: number;
  SIM_DIST: number;
  FRAMES: number;
  SPHERO_SIM_RADIUS: number;
  SIM_WIDTH: number;
  SIM_HEIGHT: number;
  EPSILON: number;
  SPHERO_SPEED: number;
  SPHERO_DIAGONAL_SPEED: number;
  ROLL_DURATION: number;
  TURN_DURATION: number;
  SIM_SPEED: number;
  ARC_ROTATION: boolean;
  MAX_MONOMERS: number;
  COLORS: {
    BLUE: [number, number, number];
    RED: [number, number, number];
    GREEN: [number, number, number];
    YELLOW: [number, number, number];
    PURPLE: [number, number, number];
    ORANGE: [number, number, number];
    BLACK: [number, number, number];
    WHITE: [number, number, number];
    GRAY: [number, number, number];
  };
  COLORS_ARRAY: [number, number, number][];
  SPHERO_TAGS: string[];
  INITIAL_POSITIONS: [number, number][];
  INITIAL_TRAITS: ("head" | "tail")[];
}

type SpheroConnectionState = "pending" | "connected" | "failed" | "not-attempted";

export interface SpheroStatus {
    id: string;
    connection: SpheroConnectionState;
    expectedPosition: [number, number];
    actualPosition: [number, number];
}