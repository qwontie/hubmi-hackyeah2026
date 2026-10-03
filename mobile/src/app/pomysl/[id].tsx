import { useLocalSearchParams } from "expo-router";
import {
  IdeaGrantAction,
  IdeaVisualisation,
} from "@/features/idea-visualisation";
import { ThreadScreen } from "@/features/thread-screen";

export default function IdeaThreadScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return (
    <ThreadScreen
      extra={
        <>
          <IdeaGrantAction id={id} />
          <IdeaVisualisation id={id} />
        </>
      }
      id={id}
      kind="idea"
    />
  );
}
