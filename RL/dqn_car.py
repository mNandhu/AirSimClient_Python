# import setup_path
import gymnasium as gym
import airgym  # noqa: F401  # ensure envs are registered via import side-effect
import time

from stable_baselines3 import DQN
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, VecTransposeImage
from stable_baselines3.common.callbacks import EvalCallback

# --- Compatibility wrapper for legacy Gym API envs (reset seed/options & step returns) ---
from typing import Any, Dict, Tuple


class GymCompatibilityWrapper(gym.Wrapper):
    """Adapts legacy Gym envs to Gymnasium API expected by SB3.

    - reset(seed=None, options=None) -> (obs, info)
    - step(action) -> (obs, reward, terminated, truncated, info)
    """

    def reset(
        self, *, seed: int | None = None, options: dict | None = None
    ) -> Tuple[Any, Dict[str, Any]]:
        # Forward reset through Gymnasium wrappers so their internal flags are set,
        # and let the underlying env handle seed/options now that it supports them.
        result = self.env.reset(seed=seed, options=options)
        if isinstance(result, tuple) and len(result) == 2:
            obs, info = result
        else:
            obs, info = result, {}
        return obs, info

    def step(self, action: Any) -> Tuple[Any, float, bool, bool, Dict[str, Any]]:
        result = self.env.step(action)
        if isinstance(result, tuple):
            try:
                n = len(result)
            except Exception:
                # Fallback: cannot measure length, coerce to zeros
                return result, float(0.0), False, False, {}

            if n == 4:
                # Legacy gym: (obs, reward, done, info)
                obs, reward, done, info = result  # type: ignore[misc,assignment]
                if isinstance(info, dict):
                    truncated = bool(info.get("TimeLimit.truncated", False))
                else:
                    truncated = False
                terminated = bool(done and not truncated)
                return (
                    obs,
                    float(reward),
                    terminated,
                    truncated,
                    info if isinstance(info, dict) else {},
                )
            elif n == 5:
                # Gymnasium: (obs, reward, terminated, truncated, info)
                obs, reward, terminated, truncated, info = result  # type: ignore[misc,assignment]
                return (
                    obs,
                    float(reward),
                    bool(terminated),
                    bool(truncated),
                    info if isinstance(info, dict) else {},
                )

        # Unknown format: try best-effort coercion
        return result, float(0.0), False, False, {}


# Create a DummyVecEnv for main airsim gym env
def make_env():
    base_env = gym.make(
        "airgym:airsim-car-sample-v0",
        ip_address="127.0.0.1",
        image_shape=(84, 84, 1),
    )
    wrapped = GymCompatibilityWrapper(base_env)
    monitored = Monitor(wrapped)
    return monitored


env = DummyVecEnv([make_env])

# Wrap env as VecTransposeImage to allow SB to handle frame observations
env = VecTransposeImage(env)

# Initialize RL algorithm type and parameters
model = DQN(
    "CnnPolicy",
    env,
    learning_rate=0.00025,
    verbose=1,
    batch_size=32,
    train_freq=4,
    target_update_interval=10000,
    learning_starts=10000,
    buffer_size=50000,
    max_grad_norm=10,
    exploration_fraction=0.1,
    exploration_final_eps=0.01,
    device="cuda",
    tensorboard_log="./tb_logs/",
)

# Create an evaluation callback with the same env, called every 10000 iterations
callbacks = []
eval_callback = EvalCallback(
    env,
    callback_on_new_best=None,
    n_eval_episodes=5,
    best_model_save_path=".",
    log_path=".",
    eval_freq=10000,
)
callbacks.append(eval_callback)

kwargs = {}
kwargs["callback"] = callbacks

# Train for a certain number of timesteps
model.learn(
    total_timesteps=500_000,
    tb_log_name="dqn_airsim_car_run_" + str(time.time()),
    **kwargs,
)

# Save policy weights
model.save("dqn_airsim_car_policy")
