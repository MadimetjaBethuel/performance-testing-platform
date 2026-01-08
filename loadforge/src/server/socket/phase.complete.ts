import { subscribe } from "./eventbus";

export const onPhaseComplete = () => {
    return subscribe((event) => {
        if (event.type === "phase_complete") {
            console.log("Phase complete event received in onPhaseComplete:", event.data);
        }
    });
}