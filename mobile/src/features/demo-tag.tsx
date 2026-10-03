import { DEMO_WORDS, useDemo } from "@/hooks/use-demo";
import { Txt } from "@/ui/text";

export function DemoTag({
  night = false,
  words = DEMO_WORDS,
}: {
  night?: boolean;
  words?: string;
}) {
  const demo = useDemo();
  if (!demo) {
    return null;
  }
  return (
    <Txt tone={night ? "onNightSoft" : "soft"} variant="small">
      {words}
    </Txt>
  );
}
