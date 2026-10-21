import React, { useEffect, useState } from "react";
import { AbsoluteFill, continueRender, delayRender } from "remotion";

// Utility composition: embeds a local Phoenix page (props.url) and waits a few seconds for it to load, so
// `remotion still PhoenixShot out.png --props='{"url":"..."}'` yields a full-resolution screenshot.
export const PhoenixShot: React.FC<{ url: string }> = ({ url }) => {
  const [handle] = useState(() => delayRender("phoenix page loading", { timeoutInMilliseconds: 60000 }));
  useEffect(() => { const t = setTimeout(() => continueRender(handle), 9000); return () => clearTimeout(t); }, [handle]);
  return <AbsoluteFill style={{ background: "#0e1320" }}><iframe src={url} style={{ width: 1920, height: 1080, border: 0 }} /></AbsoluteFill>;
};
