"""Profile management for custom PR review context."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml  # type: ignore


@dataclass
class ReviewProfile:
    """A custom context profile for PR reviews."""

    name: str
    description: str
    context: str
    created_at: str
    updated_at: str
    tags: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = []


class ProfileManager:
    """Manages custom context profiles for PR reviews."""

    def __init__(self, profiles_dir: Optional[str] = None):
        """Initialize profile manager.

        Args:
            profiles_dir: Directory to store profiles. Defaults to ~/.kit/profiles/
        """
        if profiles_dir is None:
            profiles_dir = os.path.expanduser("~/.kit/profiles")

        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def create_profile(
        self, name: str, description: str, context: str, tags: Optional[List[str]] = None
    ) -> ReviewProfile:
        """Create a new profile.

        Args:
            name: Profile name (used as filename)
            description: Human-readable description
            context: The custom context content
            tags: Optional tags for organization

        Returns:
            The created profile

        Raises:
            ValueError: If profile already exists
        """
        if not all(c.isalnum() or c in "-_" for c in name):
            raise ValueError("Profile name must contain only letters, numbers, hyphens, and underscores")

        profile_path = self.profiles_dir / f"{name}.yaml"
        if profile_path.exists():
            raise ValueError(f"Profile '{name}' already exists")

        from datetime import datetime

        timestamp = datetime.now().isoformat()

        profile = ReviewProfile(
            name=name,
            description=description,
            context=context,
            created_at=timestamp,
            updated_at=timestamp,
            tags=tags or [],
        )

        self._save_profile(profile)
        return profile

    def create_profile_from_file(
        self, name: str, description: str, file_path: str, tags: Optional[List[str]] = None
    ) -> ReviewProfile:
        """Create a profile from a file.

        Args:
            name: Profile name
            description: Human-readable description
            file_path: Path to file containing context
            tags: Optional tags for organization

        Returns:
            The created profile
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise ValueError(f"File not found: {file_path}")

        context = file_path_obj.read_text(encoding="utf-8")
        return self.create_profile(name, description, context, tags)

    def get_profile(self, name: str) -> ReviewProfile:
        """Get a profile by name.

        Args:
            name: Profile name

        Returns:
            The profile

        Raises:
            ValueError: If profile doesn't exist
        """
        profile_path = self.profiles_dir / f"{name}.yaml"
        if not profile_path.exists():
            raise ValueError(f"Profile '{name}' not found")

        with open(profile_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return ReviewProfile(**data)

    def list_profiles(self) -> List[ReviewProfile]:
        """List all profiles.

        Returns:
            List of all profiles
        """
        profiles = []
        for profile_path in self.profiles_dir.glob("*.yaml"):
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                profiles.append(ReviewProfile(**data))
            except Exception:
                # Skip invalid profiles
                continue

        return sorted(profiles, key=lambda p: p.name)

    def update_profile(
        self,
        name: str,
        description: Optional[str] = None,
        context: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> ReviewProfile:
        """Update an existing profile.

        Args:
            name: Profile name
            description: New description (optional)
            context: New context (optional)
            tags: New tags (optional)

        Returns:
            The updated profile
        """
        profile = self.get_profile(name)

        if description is not None:
            profile.description = description
        if context is not None:
            profile.context = context
        if tags is not None:
            profile.tags = tags

        from datetime import datetime

        profile.updated_at = datetime.now().isoformat()

        self._save_profile(profile)
        return profile

    def delete_profile(self, name: str) -> bool:
        """Delete a profile.

        Args:
            name: Profile name

        Returns:
            True if deleted, False if not found
        """
        profile_path = self.profiles_dir / f"{name}.yaml"
        if profile_path.exists():
            profile_path.unlink()
            return True
        return False

    def copy_profile(self, source_name: str, target_name: str) -> ReviewProfile:
        """Copy a profile to a new name.

        Args:
            source_name: Source profile name
            target_name: Target profile name

        Returns:
            The new profile
        """
        source_profile = self.get_profile(source_name)
        return self.create_profile(
            target_name,
            f"Copy of {source_profile.description}",
            source_profile.context,
            source_profile.tags.copy() if source_profile.tags else [],
        )

    def export_profile(self, name: str, output_path: str) -> None:
        """Export a profile to a file.

        Args:
            name: Profile name
            output_path: Path to export to
        """
        profile = self.get_profile(name)

        output_path_obj = Path(output_path)
        if output_path_obj.suffix.lower() == ".yaml":
            # Export as YAML with metadata
            with open(output_path_obj, "w", encoding="utf-8") as f:
                yaml.dump(profile.__dict__, f, default_flow_style=False, indent=2)
        else:
            # Export just the context content
            output_path_obj.write_text(profile.context, encoding="utf-8")

    def import_profile(self, file_path: str, name: Optional[str] = None) -> ReviewProfile:
        """Import a profile from a file.

        Args:
            file_path: Path to import from
            name: Override profile name (optional)

        Returns:
            The imported profile
        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise ValueError(f"File not found: {file_path}")

        if file_path_obj.suffix.lower() == ".yaml":
            # Import YAML with metadata
            with open(file_path_obj, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if name:
                data["name"] = name
            elif "name" not in data:
                data["name"] = file_path_obj.stem

            # Ensure required fields
            if "description" not in data:
                data["description"] = f"Imported from {file_path_obj.name}"
            if "context" not in data:
                raise ValueError("YAML file must contain 'context' field")

            return self.create_profile(data["name"], data["description"], data["context"], data.get("tags", []))
        else:
            # Import as plain text context
            context = file_path_obj.read_text(encoding="utf-8")
            profile_name = name or file_path_obj.stem

            return self.create_profile(profile_name, f"Imported from {file_path_obj.name}", context)

    def _save_profile(self, profile: ReviewProfile) -> None:
        """Save a profile to disk."""
        profile_path = self.profiles_dir / f"{profile.name}.yaml"

        with open(profile_path, "w", encoding="utf-8") as f:
            yaml.dump(profile.__dict__, f, default_flow_style=False, indent=2)
