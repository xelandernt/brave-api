from typing import List, Optional, Union, Literal, Any
from pydantic import BaseModel, Field

# Base and utility models


class Thumbnail(BaseModel):
    src: str
    original: Optional[str] = None


class Profile(BaseModel):
    name: str
    long_name: str
    url: Optional[str] = None
    img: Optional[str] = None


class Rating(BaseModel):
    ratingValue: float
    bestRating: float
    reviewCount: Optional[int] = None
    profile: Optional[Profile] = None
    is_tripadvisor: bool = True


class Thing(BaseModel):
    type: str


class Person(BaseModel):
    type: str
    email: Optional[str] = None


class MetaUrl(BaseModel):
    scheme: str
    netloc: str
    hostname: Optional[str] = None
    favicon: str
    path: str


class Contact(BaseModel):
    email: Optional[str] = None
    telephone: Optional[str] = None


class ContactPoint(Thing):
    type: Literal["contact_point"] = "contact_point"
    telephone: Optional[str] = None
    email: Optional[str] = None


class DataProvider(BaseModel):
    type: Literal["external"] = "external"
    name: str
    url: str
    long_name: Optional[str] = None
    img: Optional[str] = None


class Unit(BaseModel):
    value: float
    units: str


class Answer(BaseModel):
    text: str
    author: Optional[str] = None
    upvoteCount: Optional[int] = None
    downvoteCount: Optional[int] = None


class QAPage(BaseModel):
    question: str
    answer: Answer


class QA(BaseModel):
    question: str
    answer: str
    title: str
    url: str
    meta_url: Optional[MetaUrl] = None


class FAQ(BaseModel):
    type: Literal["faq"] = "faq"
    results: List[QA]


class ForumData(BaseModel):
    forum_name: str
    num_answers: Optional[int] = None
    score: Optional[str] = None
    title: Optional[str] = None
    question: Optional[str] = None
    top_comment: Optional[str] = None


class DiscussionResult(BaseModel):
    type: Literal["discussion"] = "discussion"
    data: Optional[ForumData] = None


class Discussions(BaseModel):
    type: Literal["search"] = "search"
    results: List[DiscussionResult]
    mutated_by_goggles: bool = False


class SearchResult(BaseModel):
    type: Literal["search_result"] = "search_result"
    subtype: str = "generic"
    is_live: bool = False
    deep_results: Optional["DeepResult"] = None
    schemas: Optional[List[List[Any]]] = None
    meta_url: Optional[MetaUrl] = None
    thumbnail: Optional[Thumbnail] = None
    age: Optional[str] = None
    language: str
    location: Optional["LocationResult"] = None
    video: Optional["VideoData"] = None
    movie: Optional["MovieData"] = None
    faq: Optional[FAQ] = None
    qa: Optional[QAPage] = None
    book: Optional["Book"] = None
    rating: Optional[Rating] = None
    article: Optional["Article"] = None
    product: Optional[Union["Product", "Review"]] = None
    product_cluster: Optional[List[Union["Product", "Review"]]] = None
    cluster_type: Optional[str] = None
    cluster: Optional[List["Result"]] = None
    creative_work: Optional["CreativeWork"] = None
    music_recording: Optional["MusicRecording"] = None
    review: Optional["Review"] = None
    software: Optional["Software"] = None
    recipe: Optional["Recipe"] = None
    organization: Optional["Organization"] = None
    content_type: Optional[str] = None
    extra_snippets: Optional[List[str]] = None


class Result(BaseModel):
    title: str
    url: str
    is_source_local: bool = True
    is_source_both: bool = True
    description: Optional[str] = None
    page_age: Optional[str] = None
    page_fetched: Optional[str] = None
    profile: Optional[Profile] = None
    language: Optional[str] = None
    family_friendly: bool = True


class LocationWebResult(Result):
    meta_url: MetaUrl


class LocationResult(Result):
    type: Literal["location_result"] = "location_result"
    id: Optional[str] = None
    provider_url: str
    coordinates: Optional[List[float]] = None
    zoom_level: int
    thumbnail: Optional[Thumbnail] = None
    postal_address: Optional["PostalAddress"] = None
    opening_hours: Optional["OpeningHours"] = None
    contact: Optional[Contact] = None
    price_range: Optional[str] = None
    rating: Optional[Rating] = None
    distance: Optional[Unit] = None
    profiles: Optional[List[DataProvider]] = None
    reviews: Optional["Reviews"] = None
    pictures: Optional["PictureResults"] = None
    action: Optional["Action"] = None
    serves_cuisine: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    icon_category: Optional[str] = None
    results: Optional[LocationWebResult] = None
    timezone: Optional[str] = None
    timezone_offset: Optional[str] = None


class Locations(BaseModel):
    type: Literal["locations"] = "locations"
    results: List[LocationResult]


class Summarizer(BaseModel):
    type: Literal["summarizer"] = "summarizer"
    key: str


class RichCallbackHint(BaseModel):
    vertical: str
    callback_key: str


class RichCallbackInfo(BaseModel):
    type: Literal["rich"] = "rich"
    hint: Optional[RichCallbackHint] = None


class ResultReference(BaseModel):
    type: str
    index: Optional[int] = None
    all: bool


class MixedResponse(BaseModel):
    type: Literal["mixed"] = "mixed"
    main: Optional[List[ResultReference]] = None
    top: Optional[List[ResultReference]] = None
    side: Optional[List[ResultReference]] = None


class LocalPoiSearchApiResponse(BaseModel):
    type: Literal["local_pois"] = "local_pois"
    results: Optional[List[LocationResult]] = None


class LocalDescriptionsSearchApiResponse(BaseModel):
    type: Literal["local_descriptions"] = "local_descriptions"
    results: Optional[List["LocationDescription"]] = None


class LocationDescription(BaseModel):
    type: Literal["local_description"] = "local_description"
    id: str
    description: Optional[str] = None


class WebSearchApiResponse(BaseModel):
    type: Literal["search"]
    discussions: Optional[Discussions] = None
    faq: Optional[FAQ] = None
    infobox: Optional["GraphInfobox"] = None
    locations: Optional[Locations] = None
    mixed: Optional[MixedResponse] = None
    news: Optional["News"] = None
    query: Optional["Query"] = None
    videos: Optional["Videos"] = None
    web: Optional["Search"] = None
    summarizer: Optional[Summarizer] = None
    rich: Optional[RichCallbackInfo] = None


class Search(BaseModel):
    type: Literal["search"] = "search"
    results: List[SearchResult]
    family_friendly: bool


class Query(BaseModel):
    original: str
    show_strict_warning: Optional[bool] = None
    altered: Optional[str] = None
    safesearch: Optional[bool] = None
    is_navigational: Optional[bool] = None
    is_geolocal: Optional[bool] = None
    local_decision: Optional[str] = None
    local_locations_idx: Optional[int] = None
    is_trending: Optional[bool] = None
    is_news_breaking: Optional[bool] = None
    ask_for_location: Optional[bool] = None
    language: Optional["Language"] = None
    spellcheck_off: Optional[bool] = None
    country: Optional[str] = None
    bad_results: Optional[bool] = None
    should_fallback: Optional[bool] = None
    lat: Optional[str] = None
    long: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    header_country: Optional[str] = None
    more_results_available: Optional[bool] = None
    custom_location_label: Optional[str] = None
    reddit_cluster: Optional[str] = None


class Language(BaseModel):
    main: str


class NewsResult(Result):
    meta_url: Optional[MetaUrl] = None
    source: Optional[str] = None
    breaking: bool
    is_live: bool
    thumbnail: Optional[Thumbnail] = None
    age: Optional[str] = None
    extra_snippets: Optional[List[str]] = None


class News(BaseModel):
    type: Literal["news"] = "news"
    results: List[NewsResult]
    mutated_by_goggles: bool = False


class VideoData(BaseModel):
    duration: Optional[str] = None
    views: Optional[str] = None
    creator: Optional[str] = None
    publisher: Optional[str] = None
    thumbnail: Optional[Thumbnail] = None
    tags: Optional[List[str]] = None
    author: Optional[Profile] = None
    requires_subscription: Optional[bool] = None


class VideoResult(Result):
    type: Literal["video_result"] = "video_result"
    video: VideoData
    meta_url: Optional[MetaUrl] = None
    thumbnail: Optional[Thumbnail] = None
    age: Optional[str] = None


class Videos(BaseModel):
    type: Literal["videos"] = "videos"
    results: List[VideoResult]
    mutated_by_goggles: Optional[bool] = False


class DeepResult(BaseModel):
    news: Optional[List[NewsResult]] = None
    buttons: Optional[List["ButtonResult"]] = None
    videos: Optional[List[VideoResult]] = None
    images: Optional[List["Image"]] = None


class ButtonResult(BaseModel):
    type: Literal["button_result"] = "button_result"
    title: str
    url: str


class ImageProperties(BaseModel):
    url: str
    resized: str
    placeholder: str
    height: Optional[int] = None
    width: Optional[int] = None
    format: Optional[str] = None
    content_size: Optional[str] = None


class Image(BaseModel):
    thumbnail: Thumbnail
    url: Optional[str] = None
    properties: Optional[ImageProperties] = None


class Review(BaseModel):
    type: Literal["review"] = "review"
    name: str
    thumbnail: Thumbnail
    description: str
    rating: Rating


class Product(BaseModel):
    type: Literal["product"] = "product"
    name: str
    category: Optional[str] = None
    price: str
    thumbnail: Thumbnail
    description: Optional[str] = None
    offers: Optional[List["Offer"]] = None
    rating: Optional[Rating] = None


class Offer(BaseModel):
    url: str
    priceCurrency: str
    price: str


class Book(BaseModel):
    title: str
    author: List[Person]
    date: Optional[str] = None
    price: Optional["Price"] = None
    pages: Optional[int] = None
    publisher: Optional[Person] = None
    rating: Optional[Rating] = None


class Price(BaseModel):
    price: str
    price_currency: str


class Article(BaseModel):
    author: Optional[List[Person]] = None
    date: Optional[str] = None
    publisher: Optional["Organization"] = None
    thumbnail: Optional[Thumbnail] = None
    isAccessibleForFree: Optional[bool] = None


class Organization(BaseModel):
    type: Literal["organization"] = "organization"
    contact_points: Optional[List[ContactPoint]] = None


class Software(BaseModel):
    name: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None
    codeRepository: Optional[str] = None
    homepage: Optional[str] = None
    datePublisher: Optional[str] = None
    is_npm: Optional[bool] = None
    is_pypi: Optional[bool] = None
    stars: Optional[int] = None
    forks: Optional[int] = None
    ProgrammingLanguage: Optional[str] = None


class MusicRecording(BaseModel):
    name: str
    thumbnail: Optional[Thumbnail] = None
    rating: Optional[Rating] = None


class MovieData(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[Thumbnail] = None
    release: Optional[str] = None
    directors: Optional[List[Person]] = None
    actors: Optional[List[Person]] = None
    rating: Optional[Rating] = None
    duration: Optional[str] = None
    genre: Optional[List[str]] = None
    query: Optional[str] = None


class PostalAddress(BaseModel):
    type: Literal["PostalAddress"] = "PostalAddress"
    country: Optional[str] = None
    postalCode: Optional[str] = None
    streetAddress: Optional[str] = None
    addressRegion: Optional[str] = None
    addressLocality: Optional[str] = None
    displayAddress: str


class DayOpeningHours(BaseModel):
    abbr_name: str
    full_name: str
    opens: str
    closes: str


class OpeningHours(BaseModel):
    current_day: Optional[List[DayOpeningHours]] = None
    days: Optional[List[List[DayOpeningHours]]] = None


class Reviews(BaseModel):
    results: List["TripAdvisorReview"]  # TripAdvisorReview
    viewMoreUrl: str
    reviews_in_foreign_language: bool


class TripAdvisorReview(BaseModel):
    title: str
    description: str
    date: str
    rating: Rating
    author: Person
    review_url: str
    language: str


class Action(BaseModel):
    type: str
    url: str


# Infobox / Graph section


class AbstractGraphInfobox(Result):
    type: str = "infobox"
    position: int
    label: Optional[str] = None
    category: Optional[str] = None
    long_desc: Optional[str] = None
    thumbnail: Optional[Thumbnail] = None
    attributes: Optional[List[List[str]]] = None
    profiles: Optional[Union[List[Profile], List[DataProvider]]] = None
    website_url: Optional[str] = None
    ratings: Optional[List[Rating]] = None
    providers: Optional[List[DataProvider]] = None
    distance: Optional[Unit] = None
    images: Optional[List[Thumbnail]] = None
    movie: Optional[MovieData] = None


class GenericInfobox(AbstractGraphInfobox):
    subtype: str = "generic"
    found_in_urls: Optional[List[str]] = None


class EntityInfobox(AbstractGraphInfobox):
    subtype: Literal["entity"] = "entity"


class QAInfobox(AbstractGraphInfobox):
    subtype: Literal["code"] = "code"
    data: QAPage
    meta_url: Optional[MetaUrl] = None


class InfoboxWithLocation(AbstractGraphInfobox):
    subtype: Literal["location"] = "location"
    is_location: bool
    coordinates: Optional[List[float]] = None
    zoom_level: int
    location: Optional[LocationResult] = None


class InfoboxPlace(AbstractGraphInfobox):
    subtype: Literal["place"] = "place"
    location: LocationResult


class GraphInfobox(BaseModel):
    type: Literal["graph"] = "graph"
    results: List[
        Union[
            GenericInfobox,
            QAInfobox,
            InfoboxPlace,
            InfoboxWithLocation,
            EntityInfobox,
        ]
    ]


class PictureResults(BaseModel):
    viewMoreUrl: Optional[str] = None
    results: List[Thumbnail]


class Recipe(BaseModel):
    title: str
    description: str
    thumbnail: Thumbnail
    url: str
    domain: str
    favicon: str
    time: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    ingredients: Optional[str] = None
    instructions: Optional[List["HowTo"]] = None
    servings: Optional[int] = None
    calories: Optional[int] = None
    rating: Optional[Rating] = None
    recipeCategory: Optional[str] = None
    recipeCuisine: Optional[str] = None
    video: Optional[VideoData] = None


class HowTo(BaseModel):
    text: str
    name: Optional[str] = None
    url: Optional[str] = None
    image: Optional[List[str]] = None


class CreativeWork(BaseModel):
    name: str
    thumbnail: Thumbnail
    rating: Optional[Rating] = None


# Resolve forward references for all relevant models
SearchResult.model_rebuild()
DeepResult.model_rebuild()
LocationResult.model_rebuild()
Product.model_rebuild()
Book.model_rebuild()
Article.model_rebuild()
Reviews.model_rebuild()
TripAdvisorReview.model_rebuild()
WebSearchApiResponse.model_rebuild()
LocalDescriptionsSearchApiResponse.model_rebuild()
Recipe.model_rebuild()
HowTo.model_rebuild()
CreativeWork.model_rebuild()


class WebSearchQueryParams(BaseModel):
    q: str = Field(
        ...,
        description="The user’s search query term. Can not be empty. Max 400 chars and 50 words.",
    )
    country: Optional[str] = Field(
        "US",
        max_length=2,
        description="2 character country code. See country codes list.",
    )
    search_lang: Optional[str] = Field(
        "en",
        min_length=2,
        description="2+ character language code. See language codes list.",
    )
    ui_lang: Optional[str] = Field(
        "en-US",
        description="Format <language_code>-<country_code> (see RFC9110 and UI language codes list).",
    )
    count: Optional[int] = Field(
        20, ge=1, le=20, description="Number of search results to return (max 20)."
    )
    offset: Optional[int] = Field(
        0, ge=0, le=9, description="Zero-based page offset (max 9)."
    )
    safesearch: Optional[str] = Field(
        "moderate",
        pattern="^(off|moderate|strict)$",
        description="Adult content filter: off, moderate, strict.",
    )
    freshness: Optional[str] = Field(
        None,
        description=(
            "Limits discovery to a time window. One of: pd (24h), pw (7d), pm (31d), py (365d), "
            "or range YYYY-MM-DDtoYYYY-MM-DD."
        ),
    )
    text_decorations: Optional[bool] = Field(
        True,
        description="Whether display strings include decoration markers (highlighting).",
    )
    spellcheck: Optional[bool] = Field(True, description="Spellcheck provided query.")
    result_filter: Optional[str] = Field(
        None,
        description=(
            "Comma delimited result types to include. E.g. discussions,faq,news,web,infobox,query,summarizer,videos,locations."
        ),
    )
    goggles_id: Optional[str] = Field(
        None,
        description="(Deprecated) Goggle for custom re-ranking (use `goggles` instead).",
    )
    goggles: Optional[List[str]] = Field(
        None, description="List of goggle URLs/definitions for custom re-ranking."
    )
    units: Optional[str] = Field(
        None,
        pattern="^(metric|imperial)$",
        description="Measurement units: metric, imperial.",
    )
    extra_snippets: Optional[bool] = Field(
        None, description="Get up to 5 additional, alternative result snippets."
    )
    summary: Optional[bool] = Field(
        None, description="Enable summary key generation in web search results."
    )


class LocalSearchQueryParams(BaseModel):
    ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of 1 to 20 non-empty unique location IDs.",
    )
    search_lang: Optional[str] = Field(
        "en",
        min_length=2,
        description="2+ character language code. See language codes list.",
    )
    ui_lang: Optional[str] = Field(
        "en-US",
        description="Format <language_code>-<country_code> (see RFC9110 and UI language codes list).",
    )
    units: Optional[str] = Field(
        None,
        pattern="^(metric|imperial)$",
        description="Measurement units: metric, imperial.",
    )
