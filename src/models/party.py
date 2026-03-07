"""Author and party role models for tracked change attribution.

Defines Pydantic models that capture who made changes in a document
and how many changes each author contributed. AuthorSummary provides
a to_prompt() method that formats the author list as a human-readable
string for Claude to read when assigning party roles.
"""

from pydantic import BaseModel, computed_field


class AuthorInfo(BaseModel):
    """Summary of a single unique author found in tracked changes.

    Captures the author's name, change counts by type, and the date
    range of their activity. The total_changes computed property
    returns the sum of all change types.
    """

    name: str
    insertion_count: int = 0
    deletion_count: int = 0
    comment_count: int = 0
    earliest_date: str = ""
    latest_date: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_changes(self) -> int:
        """Sum of insertion, deletion, and comment counts."""
        return self.insertion_count + self.deletion_count + self.comment_count


class AuthorSummary(BaseModel):
    """All authors found in the document with their change statistics.

    Provides a structured list of authors sorted by total changes
    (descending) and a to_prompt() method that formats this data
    for Claude to read during role assignment.
    """

    authors: list[AuthorInfo]

    def to_prompt(self) -> str:
        """Format the author list as a human-readable string for Claude.

        Returns a multi-line string listing each author with their
        change counts and active date range, suitable for inclusion
        in a prompt where Claude assigns party roles.
        """
        lines = ["Authors found in document:"]
        for author in self.authors:
            lines.append(
                f"  - {author.name}: {author.total_changes} changes "
                f"({author.insertion_count} ins, "
                f"{author.deletion_count} del, "
                f"{author.comment_count} comments), "
                f"active {author.earliest_date} to {author.latest_date}"
            )
        return "\n".join(lines)
