import React from "react";
import { Composition } from "remotion";
import { W, H, FPS, clipSeconds } from "./ui";
import { Hook } from "./Hook";
import { Pipeline } from "./Pipeline";
import { Recall } from "./Recall";
import { FailedIdeas } from "./FailedIdeas";
import { ReadingNumbers } from "./ReadingNumbers";
import { Takeaways } from "./Takeaways";
import { PhoenixShot } from "./PhoenixShot";
import { Thumbnail } from "./Thumbnail";
import { Seg3, Seg4, Seg8, Seg9, Seg10 } from "./LiveSegs";

// Each clip is as long as its narration audio (+2 s) -- see ../narration/build_narration.py and ../../script.md.
const CLIPS = [
  { id: "Hook", c: Hook, seg: "seg1" }, { id: "Pipeline", c: Pipeline, seg: "seg2" }, { id: "Recall", c: Recall, seg: "seg5" },
  { id: "Seg3", c: Seg3, seg: "seg3" }, { id: "Seg4", c: Seg4, seg: "seg4" }, { id: "Seg8", c: Seg8, seg: "seg8" }, { id: "Seg9", c: Seg9, seg: "seg9" }, { id: "Seg10", c: Seg10, seg: "seg10" },
  { id: "FailedIdeas", c: FailedIdeas, seg: "seg6" }, { id: "ReadingNumbers", c: ReadingNumbers, seg: "seg7" }, { id: "Takeaways", c: Takeaways, seg: "seg11" },
];
export const Root: React.FC = () => (
  <>{CLIPS.map((k) => <Composition key={k.id} id={k.id} component={k.c} durationInFrames={Math.ceil(clipSeconds(k.seg) * FPS)} fps={FPS} width={W} height={H} />)}<Composition id="Thumbnail" component={Thumbnail} durationInFrames={1} fps={FPS} width={1280} height={720} />
  <Composition id="PhoenixShot" component={PhoenixShot as React.FC<any>} durationInFrames={1} fps={FPS} width={W} height={H} defaultProps={{ url: "http://localhost:6006/projects" }} />
  </>
);
