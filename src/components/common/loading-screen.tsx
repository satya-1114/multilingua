import { Loader2 } from "lucide-react";

interface LoadingScreenProps {
  message?: string;
  fullscreen?: boolean;
}

export function LoadingScreen({ message = "Loading", fullscreen = true }: LoadingScreenProps) {
  return (
    <div
      className={
        fullscreen
          ? "flex min-h-screen items-center justify-center bg-background"
          : "flex h-full min-h-[200px] items-center justify-center"
      }
    >
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>
    </div>
  );
}
