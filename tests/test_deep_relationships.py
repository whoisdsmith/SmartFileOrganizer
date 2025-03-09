"""
Test script for deep contextual document relationship detection.
"""
import os
from ai_analyzer import AIAnalyzer

def test_deep_contextual_relationships():
    """Test the deep contextual relationship detection with more complex document relationships"""
    print("Testing deep contextual document relationship detection...")
    
    # Create a set of test documents with complex relationships
    test_documents = [
        {
            "filename": "project_proposal.txt",
            "path": "/documents/projects/proposal.txt",
            "file_type": "Text",
            "category": "Project Documentation",
            "theme": "Development",
            "keywords": ["project", "proposal", "timeline", "budget", "requirements"],
            "summary": "A project proposal for developing a new customer relationship management system with timeline, budget, and resource requirements."
        },
        {
            "filename": "technical_specifications.txt",
            "path": "/documents/projects/tech_spec.txt",
            "file_type": "Text",
            "category": "Technical Documentation",
            "theme": "Development",
            "keywords": ["technical", "specifications", "architecture", "database", "api"],
            "summary": "Technical specifications for the CRM system including database schema, API endpoints, and system architecture details."
        },
        {
            "filename": "market_research.txt",
            "path": "/documents/marketing/research.txt",
            "file_type": "Text",
            "category": "Marketing",
            "theme": "Research",
            "keywords": ["market", "research", "customer", "needs", "competitors"],
            "summary": "Market research document analyzing customer needs and competitor offerings in the CRM space."
        },
        {
            "filename": "implementation_plan.txt",
            "path": "/documents/projects/implementation.txt",
            "file_type": "Text",
            "category": "Project Documentation",
            "theme": "Implementation",
            "keywords": ["implementation", "schedule", "milestones", "resources", "tasks"],
            "summary": "Detailed implementation plan with schedule, milestones, and resource allocation for the CRM development project."
        },
        {
            "filename": "user_stories.txt",
            "path": "/documents/projects/user_stories.txt",
            "file_type": "Text",
            "category": "Requirements",
            "theme": "User Experience",
            "keywords": ["user", "stories", "requirements", "personas", "workflows"],
            "summary": "Collection of user stories and requirements defining the needed functionality and user workflows for the CRM system."
        },
        {
            "filename": "budget_approval.txt",
            "path": "/documents/finance/budget_approval.txt",
            "file_type": "Text",
            "category": "Financial",
            "theme": "Budget",
            "keywords": ["budget", "approval", "costs", "funding", "expenses"],
            "summary": "Budget approval document for the CRM project with detailed cost breakdown and funding allocation."
        },
    ]
    
    # Initialize AI analyzer with proper configuration
    print("Initializing AI analyzer...")
    ai_analyzer = AIAnalyzer()
    
    # Test finding contextual relationships beyond simple keyword matching
    print("\nTesting deep contextual relationship detection:")
    target_doc = test_documents[0]  # Project proposal
    print(f"Target document: {target_doc['filename']}")
    print(f"Summary: {target_doc['summary']}")
    
    print("\nFinding related documents using deep contextual analysis...")
    related_content = ai_analyzer.find_related_content(target_doc, test_documents)
    related_docs = related_content.get('related_documents', [])
    
    print(f"Relationship type: {related_content.get('relationship_type', 'N/A')}")
    print(f"Overall strength: {related_content.get('relationship_strength', 'N/A')}")
    print(f"\nFound {len(related_docs)} related documents:")
    
    for i, doc in enumerate(related_docs):
        print(f"\n{i+1}. {doc['filename']}")
        if 'relationship_type' in doc:
            print(f"   Type: {doc.get('relationship_type', 'N/A')}")
        print(f"   Strength: {doc.get('relationship_strength', 'N/A')}")
        print(f"   Explanation: {doc.get('relationship_explanation', 'N/A')}")
        print(f"   Similarity Score: {doc.get('similarity_score', 'N/A')}")
    
    # Now test with a different target document to show different relationships
    another_target = test_documents[4]  # User stories
    print(f"\n\nTesting with different target document: {another_target['filename']}")
    print(f"Summary: {another_target['summary']}")
    
    print("\nFinding related documents...")
    another_related = ai_analyzer.find_related_content(another_target, test_documents)
    another_docs = another_related.get('related_documents', [])
    
    print(f"Relationship type: {another_related.get('relationship_type', 'N/A')}")
    print(f"Overall strength: {another_related.get('relationship_strength', 'N/A')}")
    print(f"\nFound {len(another_docs)} related documents:")
    
    for i, doc in enumerate(another_docs):
        print(f"\n{i+1}. {doc['filename']}")
        if 'relationship_type' in doc:
            print(f"   Type: {doc.get('relationship_type', 'N/A')}")
        print(f"   Strength: {doc.get('relationship_strength', 'N/A')}")
        print(f"   Explanation: {doc.get('relationship_explanation', 'N/A')}")
        print(f"   Similarity Score: {doc.get('similarity_score', 'N/A')}")
    
    print("\nDeep contextual relationship testing completed successfully!")

if __name__ == "__main__":
    test_deep_contextual_relationships()