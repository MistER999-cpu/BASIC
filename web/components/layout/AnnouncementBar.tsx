"use client";

import { useEffect, useState } from "react";
import { site } from "@/lib/site";

/** Rotates the announcements on a slow timer; pauses while the tab is hidden. */
export function AnnouncementBar() {
  const messages = site.announcements;
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (messages.length < 2) return;
    const id = window.setInterval(() => {
      if (document.hidden) return;
      setIndex((i) => (i + 1) % messages.length);
    }, 5200);
    return () => window.clearInterval(id);
  }, [messages.length]);

  return (
    <div className="bg-ink text-paper">
      <div className="mx-auto flex h-9 max-w-[130rem] items-center justify-center px-5">
        <p key={index} className="label animate-[var(--animate-rise)] text-center">
          {messages[index]}
        </p>
      </div>
    </div>
  );
}
