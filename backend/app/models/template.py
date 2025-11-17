"""
Template models for structured document summarization.

Templates define the structure and AI guidance for different types of summaries.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId


class TemplateSection(BaseModel):
    """A single section within a template."""

    title: str = Field(..., description="Section heading (e.g., 'References', 'Technical Aspects')")
    guidance_prompt: str = Field(
        ...,
        description="Detailed instructions for the AI on what to search for and how to synthesize this section"
    )
    order: int = Field(..., description="Display order of this section in the final output")
    required: bool = Field(default=True, description="Whether this section is mandatory")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Estimated Costs",
                "guidance_prompt": "Search for 'costs', 'capital cost', 'operating cost', 'O&M', 'tariffs', 'unit reference values (URVs)', 'N$', 'US$'. Extract and summarize any financial data related to the project's cost.",
                "order": 7,
                "required": True
            }
        }


class ProcessingStrategy(BaseModel):
    """Defines how the AI should process documents with this template."""

    approach: str = Field(
        default="multi-pass",
        description="Processing approach: 'multi-pass' (index then query), 'sequential' (chunk-by-chunk), or 'hybrid'"
    )
    chunk_size: int = Field(default=500, description="Target size for text chunks in words")
    overlap: int = Field(default=50, description="Number of words to overlap between chunks")
    embedding_model: str = Field(default="text-embedding-3-small", description="OpenAI embedding model to use")
    summarization_model: str = Field(default="gpt-4o-mini", description="OpenAI model for summarization")
    max_tokens_per_section: int = Field(default=1500, description="Maximum tokens for each section summary")
    temperature: float = Field(default=0.3, description="Temperature for AI generation (0.0-1.0)")

    class Config:
        json_schema_extra = {
            "example": {
                "approach": "multi-pass",
                "chunk_size": 500,
                "overlap": 50,
                "embedding_model": "text-embedding-3-small",
                "summarization_model": "gpt-4o-mini",
                "max_tokens_per_section": 1500,
                "temperature": 0.3
            }
        }


class TemplateBase(BaseModel):
    """Base template model with common fields."""

    name: str = Field(..., description="Template name (e.g., 'Feasibility Study Summary')")
    description: str = Field(..., description="Detailed description of what this template produces")
    target_length: str = Field(..., description="Expected length (e.g., '10 pages', '2-3 pages', '1 page')")
    category: str = Field(default="general", description="Template category: 'engineering', 'business', 'legal', 'general'")
    sections: List[TemplateSection] = Field(..., description="Ordered list of sections to generate")
    processing_strategy: ProcessingStrategy = Field(
        default_factory=ProcessingStrategy,
        description="AI processing configuration"
    )
    system_prompt: str = Field(
        default="You are an expert technical consultant specializing in document analysis and synthesis.",
        description="Base system prompt for the AI when using this template"
    )
    is_active: bool = Field(default=True, description="Whether this template is available for use")
    is_default: bool = Field(default=False, description="Whether this is the default template")

    class Config:
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }


class TemplateCreate(TemplateBase):
    """Model for creating a new template."""
    pass


class TemplateUpdate(BaseModel):
    """Model for updating an existing template."""

    name: Optional[str] = None
    description: Optional[str] = None
    target_length: Optional[str] = None
    category: Optional[str] = None
    sections: Optional[List[TemplateSection]] = None
    processing_strategy: Optional[ProcessingStrategy] = None
    system_prompt: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class TemplateInDB(TemplateBase):
    """Template model as stored in database."""

    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    created_by: Optional[ObjectId] = Field(None, description="User ID who created this template")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    usage_count: int = Field(default=0, description="Number of times this template has been used")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }


class TemplateResponse(BaseModel):
    """Template model for API responses."""

    id: str = Field(alias="_id", serialization_alias="id")
    name: str
    description: str
    target_length: str
    category: str
    sections: List[TemplateSection]
    processing_strategy: ProcessingStrategy
    system_prompt: str
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime
    usage_count: int

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


# Pre-defined templates for seeding the database
FEASIBILITY_STUDY_TEMPLATE = TemplateCreate(
    name="Feasibility Study Summary",
    description="A comprehensive ~10-page technical summary of a feasibility study, designed for engineering and strategic review.",
    target_length="10 pages",
    category="engineering",
    system_prompt="You are a senior civil engineering consultant specializing in water resource management and infrastructure projects. Your expertise includes technical analysis, cost estimation, and strategic planning for large-scale engineering schemes.",
    processing_strategy=ProcessingStrategy(
        approach="multi-pass",
        chunk_size=600,
        overlap=75,
        embedding_model="text-embedding-3-small",
        summarization_model="gpt-4o-mini",
        max_tokens_per_section=2000,
        temperature=0.2  # Lower for more factual, technical output
    ),
    sections=[
        TemplateSection(
            title="References",
            guidance_prompt="Scan the document for a 'References' or 'Literature' section. Extract the list of cited sources. Format them as a simple list. If no specific section exists, state 'References are cited throughout the document.'",
            order=1,
            required=True
        ),
        TemplateSection(
            title="Scheme Locality",
            guidance_prompt="Search the document for maps, figures, or text describing the project's physical location (e.g., 'Central Coastal Area', 'Erongo Region', 'Von Bach Dam'). Summarize the geographic scope. Identify any layout maps (e.g., Figure 1.1, Figure 5.1) by their figure number and title, and state that they are present in the source document.",
            order=2,
            required=True
        ),
        TemplateSection(
            title="Overview Description of the Intervention",
            guidance_prompt="Synthesize the Executive Summary and Introduction sections. Explain the core problem (e.g., water deficits) and the proposed solution (e.g., desalination plant, water carriage system). Identify the main project scenarios (e.g., SS1, SS2, SS3). This should be a high-level summary of 'what' and 'why'.",
            order=3,
            required=True
        ),
        TemplateSection(
            title="Saving or Yield",
            guidance_prompt="Search for terms like 'yield', 'Mm³/a', 'sustainable yield', 'abstraction rates', 'water deficits', 'augmentation volumes'. Extract key figures for existing sources (groundwater, surface water) and the projected deficit that the new scheme must cover. Reference key tables (e.g., Table E1, Table 5.12, Table 6.1).",
            order=4,
            required=True
        ),
        TemplateSection(
            title="Technical Scheme Aspects",
            guidance_prompt="Synthesize information on the physical components of the proposed project. Search for: \n- **Components & Sizing:** 'pipeline', 'pump stations', 'reservoirs', 'desalination plant'. \n- **Operational Aspects:** 'operations', 'maintenance', 'water transfer'. \n- **Water Quality:** 'TDS', 'water quality', 'treatment', 'potable standards'. \n- **Implementation:** 'phases', 'timeline', 'programme'. Summarize each of these sub-topics.",
            order=5,
            required=True
        ),
        TemplateSection(
            title="Socio-economic and Environmental Considerations",
            guidance_prompt="Search for sections discussing 'socio-economic', 'demographic', 'environmental', 'stakeholder feedback', 'legal and policy'. Summarize key findings regarding population growth, economic impact, legal frameworks (e.g., Water Act), and stakeholder concerns (e.g., affordability, tariffs).",
            order=6,
            required=True
        ),
        TemplateSection(
            title="Estimated Costs",
            guidance_prompt="Search for 'costs', 'capital cost', 'operating cost', 'O&M', 'tariffs', 'unit reference values (URVs)', 'N$', 'US$'. Extract and summarize any financial data related to the project's cost. State the estimated capital and operational costs if available, and mention the factors influencing them.",
            order=7,
            required=True
        ),
        TemplateSection(
            title="Strengths and Weaknesses",
            guidance_prompt="This requires inference. Analyze the text for positive and negative aspects. Search for terms like 'strengths', 'advantages', 'benefits', AND 'weaknesses', 'risks', 'concerns', 'challenges', 'disadvantages'. Synthesize these points into two distinct lists: Strengths and Weaknesses.",
            order=8,
            required=True
        ),
        TemplateSection(
            title="Strategic Considerations",
            guidance_prompt="Review the 'Conclusions and Recommendations' sections. Synthesize the high-level strategic takeaways for decision-makers. What are the key recommendations? What future actions are required? This section should summarize the 'so what' of the entire report.",
            order=9,
            required=True
        )
    ],
    is_default=True,
    is_active=True
)


EXECUTIVE_SUMMARY_TEMPLATE = TemplateCreate(
    name="Executive Summary",
    description="A concise 1-2 page executive summary highlighting key points and recommendations.",
    target_length="1-2 pages",
    category="general",
    system_prompt="You are an executive consultant who excels at distilling complex documents into clear, actionable summaries for senior leadership.",
    processing_strategy=ProcessingStrategy(
        approach="sequential",
        summarization_model="gpt-4o-mini",
        max_tokens_per_section=800,
        temperature=0.4
    ),
    sections=[
        TemplateSection(
            title="Key Findings",
            guidance_prompt="Identify and summarize the 3-5 most important findings or conclusions from the document.",
            order=1,
            required=True
        ),
        TemplateSection(
            title="Recommendations",
            guidance_prompt="Extract and list the main recommendations or action items proposed in the document.",
            order=2,
            required=True
        ),
        TemplateSection(
            title="Next Steps",
            guidance_prompt="Identify any timeline, milestones, or immediate next steps mentioned in the document.",
            order=3,
            required=False
        )
    ],
    is_default=False,
    is_active=True
)
