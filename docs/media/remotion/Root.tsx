import React from "react";
import { Composition, Still } from "remotion";
import { PathFinderVideo, totalFrames, FPS } from "./PathFinder";
import { Slide, SLIDE_COUNT } from "./slides";

export const PFRoot: React.FC = () => (
  <>
    <Composition id="PathFinder" component={PathFinderVideo} durationInFrames={totalFrames()} fps={FPS} width={1920} height={1080} defaultProps={{ captions: true }} />
    {Array.from({ length: SLIDE_COUNT }, (_, i) => (
      <Still key={i} id={`Slide${i + 1}`} component={Slide} width={1920} height={1080} defaultProps={{ n: i + 1 }} />
    ))}
  </>
);
